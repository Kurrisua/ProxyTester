package utils

import (
	"bufio"
	"bytes"
	"context"
	"crypto/tls"
	"fmt"
	"io"
	"net"
	"net/http"
	"net/url"
	"os"
	"strings"
	"time"

	"golang.org/x/net/proxy"
)

// 防止goroutine 异步处理问题
func addSocks(socks5 string, source string) {
	Mu.Lock()
	SocksList = append(SocksList, ProxyInfo{
		Addr:   socks5,
		Source: source,
	})
	Mu.Unlock()
}
func fetchContent(baseURL string, method string, timeout int, urlParams map[string]string, headers map[string]string, jsonBody string) (string, error) {
	client := &http.Client{
		Transport: &http.Transport{
			TLSClientConfig: &tls.Config{InsecureSkipVerify: true},
		},
		Timeout: time.Duration(timeout) * time.Second,
	}
	u, err := url.Parse(baseURL)
	if err != nil {
		return "", err
	}
	if urlParams != nil {
		q := u.Query()
		for key, value := range urlParams {
			q.Set(key, value)
		}
		u.RawQuery = q.Encode()
	}

	var req *http.Request
	if jsonBody != "" {
		req, err = http.NewRequest(method, u.String(), bytes.NewBufferString(jsonBody))
	} else {
		req, err = http.NewRequest(method, u.String(), nil)
	}

	if err != nil {
		return "", err
	}
	req.Header.Add("User-Agent", "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Safari/537.36 Edg/112.0.1722.17")
	if len(headers) != 0 {
		for key, value := range headers {
			req.Header.Add(key, value)
		}
	}
	resp, err := client.Do(req)
	if err != nil {
		return "", err
	}
	defer resp.Body.Close()

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return "", err
	}
	return string(body), nil
}

func RemoveDuplicates() {
	seen := make(map[string]struct{})
	var result []ProxyInfo
	for _, sock := range SocksList {
		if _, ok := seen[sock.Addr]; !ok {
			result = append(result, sock)
			seen[sock.Addr] = struct{}{}
		}
	}

	SocksList = result
}

func CheckSocks(checkSocks CheckSocksConfig) {
	maxConcurrentReq := checkSocks.MaxConcurrentReq
	timeout := checkSocks.Timeout
	semaphore = make(chan struct{}, maxConcurrentReq)

	checkRspKeywords := checkSocks.CheckRspKeywords
	checkGeolocateConfig := checkSocks.CheckGeolocate
	checkGeolocateSwitch := checkGeolocateConfig.Switch
	isOpenGeolocateSwitch := false
	reqUrl := checkSocks.CheckURL
	if checkGeolocateSwitch == "open" {
		isOpenGeolocateSwitch = true
		reqUrl = checkGeolocateConfig.CheckURL
	}
	fmt.Printf("并发:[ %v ],超时标准:[ %vs ]\n", maxConcurrentReq, timeout)

	for index, pInfo := range SocksList { // 修改：直接遍历 SocksList 获取 ProxyInfo 对象
		Wg.Add(1)
		semaphore <- struct{}{}

		// 修改：匿名函数接收整个 ProxyInfo 对象 p，以及当前索引 i
		go func(p ProxyInfo, i int) {
			Mu.Lock()
			fmt.Printf("\r正检测第 [ %v/%v ] 个代理,异步处理中...                    ", i+1, len(SocksList))
			Mu.Unlock()

			defer Wg.Done()
			defer func() {
				<-semaphore
			}()

			socksProxy := "socks5://" + p.Addr // 使用 p.Addr
			proxy := func(_ *http.Request) (*url.URL, error) {
				return url.Parse(socksProxy)
			}
			tr := &http.Transport{
				TLSClientConfig: &tls.Config{InsecureSkipVerify: true},
				Proxy:           proxy,
			}
			client := &http.Client{
				Transport: tr,
				Timeout:   time.Duration(timeout) * time.Second,
			}
			req, err := http.NewRequest("GET", reqUrl, nil)
			if err != nil {
				return
			}
			req.Header.Add("User-Agent", "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Safari/537.36 Edg/112.0.1722.17")
			resp, err := client.Do(req)
			if err != nil {
				return
			}
			defer resp.Body.Close()

			body, err := io.ReadAll(resp.Body)
			if err != nil {
				return
			}
			stringBody := string(body)
			if !isOpenGeolocateSwitch {
				if !strings.Contains(stringBody, checkRspKeywords) {
					return
				}
			} else {
				for _, keyword := range checkGeolocateConfig.ExcludeKeywords {
					if strings.Contains(stringBody, keyword) {
						return
					}
				}
				for _, keyword := range checkGeolocateConfig.IncludeKeywords {
					if !strings.Contains(stringBody, keyword) {
						return
					}
				}
			}

			Mu.Lock()
			// 修复：直接将完整的对象 p (包含 Addr 和 Source) 存入有效列表
			EffectiveList = append(EffectiveList, p)
			Mu.Unlock()
		}(pInfo, index) // 传入当前对象和索引
	}
	Wg.Wait()
}

func WriteLinesToFile() error {
	file, err := os.Create(LastDataFile)
	if err != nil {
		return err
	}
	defer file.Close()

	writer := bufio.NewWriter(file)
	for _, p := range EffectiveList {
		// 格式：IP:PORT 来源 2006-01-02_15:04:05
		line := fmt.Sprintf("%s %s\n", p.Addr, p.Source)
		if _, err := writer.WriteString(line); err != nil {
			return err
		}
	}

	return writer.Flush()
}

func DefineDial(ctx context.Context, network, address string) (net.Conn, error) {

	return transmitReqFromClient(network, address)
}

// 修改获取代理的打印逻辑，方便观察来源
func transmitReqFromClient(network string, address string) (net.Conn, error) {
	tempProxy := getNextProxy()

	// 查找当前代理的来源
	source := "unknown"
	Mu.Lock()
	for _, p := range EffectiveList {
		if p.Addr == tempProxy {
			source = p.Source
			break
		}
	}
	Mu.Unlock()

	// 打印格式：时间 [来源] -> 代理地址
	fmt.Printf("%s [%-7s] -> %s\n", time.Now().Format("15:04:05"), source, tempProxy)

	timeout := time.Duration(Timeout) * time.Second
	dialer := &net.Dialer{Timeout: timeout}
	dialect, _ := proxy.SOCKS5(network, tempProxy, nil, dialer)
	conn, err := dialect.Dial(network, address)
	if err != nil {
		delInvalidProxy(tempProxy)
		fmt.Printf("%s 无效，自动切换下一个......\n", tempProxy)
		return transmitReqFromClient(network, address)
	}
	return conn, nil
}

func getNextProxy() string {
	Mu.Lock()
	defer Mu.Unlock()
	if len(EffectiveList) == 0 {
		fmt.Println("***已无可用代理，程序退出***")
		os.Exit(1)
	}
	if len(EffectiveList) <= 2 {
		fmt.Printf("***可用代理已仅剩%v个,%v，***\n", len(EffectiveList), EffectiveList)
	}
	proxy := EffectiveList[ProxyIndex]
	ProxyIndex = (ProxyIndex + 1) % len(EffectiveList) // 循环访问
	return proxy.Addr
}

// 使用过程中删除无效的代理
func delInvalidProxy(proxy string) {
	Mu.Lock()
	for i, p := range EffectiveList {
		if p.Addr == proxy {
			EffectiveList = append(EffectiveList[:i], EffectiveList[i+1:]...)
			if ProxyIndex != 0 {
				ProxyIndex = ProxyIndex - 1
			}
			break
		}
	}
	if ProxyIndex >= len(EffectiveList) {
		ProxyIndex = 0
	}
	Mu.Unlock()
}

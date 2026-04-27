package main

import (
	"Deadpool/utils"
	"fmt"
	"io"
	"log"
	"os"
	"strconv"
	"strings"

	"github.com/armon/go-socks5"
)

func main() {
	utils.Banner()
	fmt.Print("By:thinkoaa GitHub:https://github.com/thinkoaa/Deadpool\n\n\n")

	// 解析命令行参数
	configPath := "config.toml"
	help := false

	// 定义三个文件路径
	lastDataPath1 := "lastData.txt"
	lastDataPath2 := "http.txt"    // 第二个文件
	lastDataPath3 := "git.txt"      // 第三个文件

	for i := 1; i < len(os.Args); i++ {
		arg := os.Args[i]
		if arg == "-h" || arg == "--help" {
			help = true
		} else if arg == "-c" || arg == "--config" {
			if i+1 < len(os.Args) {
				configPath = os.Args[i+1]
				i++
			}
		} else if arg == "-l" || arg == "--lastdata" {
			// 保持兼容性，如果指定了-l参数，就只使用一个文件
			if i+1 < len(os.Args) {
				lastDataPath1 = os.Args[i+1]
				utils.LastDataFile = lastDataPath1
				i++
			}
		}
	}

	if help {
		fmt.Println("Deadpool 代理池工具 使用帮助:")
		fmt.Println("  -h, --help          显示此帮助信息")
		fmt.Println("  -c, --config <path> 指定配置文件路径 (默认: config.toml)")
		fmt.Println("  -l, --lastdata <path> 指定lastdata文件路径 (默认: lastData.txt)")
		fmt.Println("                       使用此选项时，不会重新从网络空间获取代理")
		fmt.Println("  默认会读取三个文件: lastData.txt, http.txt, git.txt")
		os.Exit(0)
	}

	// 读取配置文件
	config, err := utils.LoadConfig(configPath)
	if err != nil {
		fmt.Printf("配置文件 %s 存在错误: %v\n", configPath, err)
		os.Exit(1)
	}

	// 从本地文件中取socks代理
	fmt.Print("***直接使用fmt打印当前使用的代理,若高并发时,命令行打印可能会阻塞，不对打印做特殊处理，可忽略，不会影响实际的请求转发***\n\n")

	if lastDataPath1 == utils.LastDataFile {
		// 未指定自定义lastdata路径时，从网络空间获取代理

		// 从多个本地文件获取代理
		utils.GetSocksFromFile(lastDataPath1) // 读取 lastData.txt
		utils.GetSocksFromFile(lastDataPath2) // 读取 http.txt
		utils.GetSocksFromFile(lastDataPath3) // 读取 git.txt

		// 从网络空间获取代理
		utils.Wg.Add(3)
		go utils.GetSocksFromQuake(config.QUAKE)
		go utils.GetSocksFromFofa(config.FOFA)
		go utils.GetSocksFromHunter(config.HUNTER)
		utils.Wg.Wait()
	} else {
		// 从指定的单个本地文件获取代理
		utils.GetSocksFromFile(lastDataPath1)
	}

	if len(utils.SocksList) == 0 {
		fmt.Println("未发现代理数据,请调整配置信息,或向以下文件中直接写入IP:PORT格式的socks5代理：")
		fmt.Printf("  - %s\n", lastDataPath1)
		fmt.Printf("  - %s\n", lastDataPath2)
		fmt.Printf("  - %s\n", lastDataPath3)
		os.Exit(1)
	}
	fmt.Printf("根据IP:PORT去重后，共发现%v个代理\n跳过可用性检测，直接使用所有代理\n", len(utils.SocksList))

	// 跳过检测代理存活性，直接将所有代理添加到有效列表
	utils.EffectiveList = append(utils.EffectiveList, utils.SocksList...)

	if len(utils.EffectiveList) == 0 {
		fmt.Println("未发现代理数据,程序退出")
		os.Exit(1)
	}

	utils.WriteLinesToFile() //存活代理写入硬盘，以备下次启动直接读取

	// 开启监听
	conf := &socks5.Config{
		Dial:   utils.DefineDial,
		Logger: log.New(io.Discard, "", log.LstdFlags),
	}
	userName := strings.TrimSpace(config.Listener.UserName)
	password := strings.TrimSpace(config.Listener.Password)
	if userName != "" && password != "" {
		cator := socks5.UserPassAuthenticator{Credentials: socks5.StaticCredentials{
			userName: password,
		}}
		conf.AuthMethods = []socks5.Authenticator{cator}
	}
	server, _ := socks5.New(conf)
	listener := config.Listener.IP + ":" + strconv.Itoa(config.Listener.Port)
	fmt.Printf("======其他工具通过配置 socks5://%v 使用收集的代理,如有账号密码，记得配置======\n", listener)
	fmt.Println("按回车键切换到下一个代理IP...")

	// 使用goroutine监听键盘输入
	go func() {
		for {
			var input string
			fmt.Scanln(&input)
			// 切换到下一个代理
			utils.Mu.Lock()
			utils.ProxyIndex = (utils.ProxyIndex + 1) % len(utils.EffectiveList)
			currentIndex := utils.ProxyIndex
			utils.Mu.Unlock()
			if len(utils.EffectiveList) > 0 {
				fmt.Printf("已切换到代理IP: %s (索引: %d/%d)\n", utils.EffectiveList[currentIndex], currentIndex+1, len(utils.EffectiveList))
			} else {
				fmt.Println("没有可用的代理IP")
			}
			fmt.Println("按回车键切换到下一个代理IP...")
		}
	}()

	if err := server.ListenAndServe("tcp", listener); err != nil {
		fmt.Printf("本地监听服务启动失败：%v\n", err)
		os.Exit(1)
	}

}
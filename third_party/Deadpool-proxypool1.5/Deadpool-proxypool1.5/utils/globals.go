package utils

import "sync"

type ProxyInfo struct {
	Addr   string
	Source string
}

var (
	SocksList     []ProxyInfo // 修改为结构体切片
	EffectiveList []ProxyInfo // 修改为结构体切片
	ProxyIndex    int
	Timeout       int
	LastDataFile  = "lastData.txt"
	Wg            sync.WaitGroup
	Mu            sync.Mutex
	semaphore     chan struct{}
)

func Banner() {
	banner := `
   ____                        __                          ___      
  /\ $_$\                     /\ \                        /\_ \     
  \ \ \/\ \     __     __     \_\ \  _____     ___     ___\//\ \    
   \ \ \ \ \  /@__@\ /^__^\   />_< \/\ -__-\  /*__*\  /'__'\\ \ \   
    \ \ \_\ \/\  __//\ \_\.\_/\ \-\ \ \ \_\ \/\ \-\ \/\ \_\ \\-\ \_ 
     \ \____/\ \____\ \__/.\_\ \___,_\ \ ,__/\ \____/\ \____//\____\
      \/___/  \/____/\/__/\/_/\/__,_ /\ \ \/  \/___/  \/___/ \/____/
                                       \ \_\                        
                                        \/_/                        
`
	print(banner)
}

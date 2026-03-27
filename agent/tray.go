package main

import (
	_ "embed"
	"fmt"
	"log"
	"net/url"
	"os/exec"
	"runtime"
	"time"

	"github.com/getlantern/systray"
)

//go:embed assets/icon.png
var trayIcon []byte

type TrayApp struct {
	uploader *Uploader
	queue    *JobQueue
	cfg      *ConfigStore
	quitFn   func()
}

func NewTrayApp(uploader *Uploader, queue *JobQueue, cfg *ConfigStore, quitFn func()) *TrayApp {
	return &TrayApp{uploader: uploader, queue: queue, cfg: cfg, quitFn: quitFn}
}

func (t *TrayApp) Run() {
	systray.Run(t.onReady, func() {})
}

func (t *TrayApp) onReady() {
	systray.SetTemplateIcon(trayIcon, trayIcon)
	systray.SetIcon(trayIcon)
	systray.SetTitle("Indygestion")
	systray.SetTooltip("Indygestion upload agent")

	statusItem := systray.AddMenuItem("Status: initializing...", "status")
	statusItem.Disable()
	pauseAll := systray.AddMenuItem("Pause All", "Pause all uploads")
	resumeAll := systray.AddMenuItem("Resume All", "Resume all uploads")
	systray.AddSeparator()
	openWebUI := systray.AddMenuItem("Open Web UI", "Open web UI")
	settings := systray.AddMenuItem("Settings...", "Open settings endpoint")
	systray.AddSeparator()
	quitItem := systray.AddMenuItem("Quit", "Quit app")

	go func() {
		for {
			select {
			case <-pauseAll.ClickedCh:
				t.uploader.PauseAll()
			case <-resumeAll.ClickedCh:
				t.uploader.ResumeAll()
			case <-openWebUI.ClickedCh:
				_ = openBrowser(baseURL(t.cfg.Get().ServerURL))
			case <-settings.ClickedCh:
				_ = openBrowser(fmt.Sprintf("http://127.0.0.1:%d/api/config", t.cfg.Get().ListenPort))
			case <-quitItem.ClickedCh:
				t.quitFn()
				systray.Quit()
				return
			}
		}
	}()

	go func() {
		ticker := time.NewTicker(2 * time.Second)
		defer ticker.Stop()
		for range ticker.C {
			jobs, err := t.queue.List()
			if err != nil {
				log.Printf("tray status error: %v", err)
				continue
			}
			var uploading, queued int
			var avg float64
			for _, j := range jobs {
				if j.Status == StatusUploading {
					uploading++
					avg += j.Progress
				}
				if j.Status == StatusQueued {
					queued++
				}
			}
			if uploading > 0 {
				avg /= float64(uploading)
			}
			tooltip := fmt.Sprintf("Indygestion: %d uploading (%.0f%%) | %d queued", uploading, avg, queued)
			systray.SetTooltip(tooltip)
			statusItem.SetTitle(fmt.Sprintf("Status: %d uploading, %d queued", uploading, queued))
		}
	}()
}

func baseURL(raw string) string {
	u, err := url.Parse(raw)
	if err != nil {
		return raw
	}
	u.Path = ""
	u.RawQuery = ""
	u.Fragment = ""
	return u.String()
}

func openBrowser(link string) error {
	switch runtime.GOOS {
	case "windows":
		return exec.Command("rundll32", "url.dll,FileProtocolHandler", link).Start()
	case "darwin":
		return exec.Command("open", link).Start()
	default:
		return exec.Command("xdg-open", link).Start()
	}
}

package main

import (
	"context"
	"fmt"
	"log"
	"net/http"
	"os"
	"os/signal"
	"syscall"
)

func main() {
	cfgStore, err := NewConfigStore()
	if err != nil {
		log.Fatal(err)
	}
	queue, err := NewJobQueue()
	if err != nil {
		log.Fatal(err)
	}
	defer queue.Close()

	notifier := NewNotifier()
	network := NewNetworkMonitor(cfgStore)
	uploader := NewUploader(queue, cfgStore, notifier, network)

	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()
	network.Start(ctx)
	uploader.Start(ctx)

	api := NewAPIServer(cfgStore, queue, uploader, network)
	srv := &http.Server{
		Addr:    fmt.Sprintf("127.0.0.1:%d", cfgStore.Get().ListenPort),
		Handler: api.Handler(),
	}

	go func() {
		log.Printf("API listening on %s", srv.Addr)
		if err := srv.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			log.Printf("http server error: %v", err)
		}
	}()

	shutdown := make(chan os.Signal, 1)
	signal.Notify(shutdown, syscall.SIGINT, syscall.SIGTERM)

	tray := NewTrayApp(uploader, queue, cfgStore, func() {
		uploader.Shutdown()
		cancel()
		_ = srv.Shutdown(context.Background())
	})
	go tray.Run()

	<-shutdown
	uploader.Shutdown()
	cancel()
	_ = srv.Shutdown(context.Background())
}

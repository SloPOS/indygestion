package main

import (
	"context"
	"net/http"
	"sync"
	"time"
)

type NetworkEvent struct {
	Online bool
}

type NetworkMonitor struct {
	cfgStore *ConfigStore
	client   *http.Client
	online   bool
	mu       sync.RWMutex
	events   chan NetworkEvent
}

func NewNetworkMonitor(cfgStore *ConfigStore) *NetworkMonitor {
	return &NetworkMonitor{
		cfgStore: cfgStore,
		client:   &http.Client{Timeout: 5 * time.Second},
		online:   true,
		events:   make(chan NetworkEvent, 8),
	}
}

func (n *NetworkMonitor) Events() <-chan NetworkEvent { return n.events }

func (n *NetworkMonitor) IsOnline() bool {
	n.mu.RLock()
	defer n.mu.RUnlock()
	return n.online
}

func (n *NetworkMonitor) Start(ctx context.Context) {
	go func() {
		cfg := n.cfgStore.Get()
		ticker := time.NewTicker(time.Duration(cfg.NetworkCheckIntervalSeconds) * time.Second)
		defer ticker.Stop()
		for {
			select {
			case <-ctx.Done():
				return
			case <-ticker.C:
				n.check()
			}
		}
	}()
}

func (n *NetworkMonitor) check() {
	cfg := n.cfgStore.Get()
	req, _ := http.NewRequest(http.MethodHead, cfg.ServerURL, nil)
	req.Header.Set("Tus-Resumable", "1.0.0")
	resp, err := n.client.Do(req)
	nowOnline := err == nil && resp != nil && resp.StatusCode < 500
	if resp != nil {
		_ = resp.Body.Close()
	}
	changed := false
	n.mu.Lock()
	if n.online != nowOnline {
		n.online = nowOnline
		changed = true
	}
	n.mu.Unlock()
	if changed {
		n.events <- NetworkEvent{Online: nowOnline}
	}
}

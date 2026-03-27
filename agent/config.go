package main

import (
	"encoding/json"
	"errors"
	"os"
	"path/filepath"
	"runtime"
	"sync"
)

type Config struct {
	ServerURL                   string `json:"serverUrl"`
	ListenPort                  int    `json:"listenPort"`
	ChunkSizeMb                 int64  `json:"chunkSizeMb"`
	MaxConcurrent               int    `json:"maxConcurrent"`
	AutoRetry                   bool   `json:"autoRetry"`
	MaxRetries                  int    `json:"maxRetries"`
	RetryDelaySeconds           int    `json:"retryDelaySeconds"`
	NetworkCheckIntervalSeconds int    `json:"networkCheckIntervalSeconds"`
	AutoStartOnBoot             bool   `json:"autoStartOnBoot"`
}

func DefaultConfig() Config {
	return Config{
		ServerURL:                   "http://127.0.0.1:1080/files/",
		ListenPort:                  4709,
		ChunkSizeMb:                 50,
		MaxConcurrent:               2,
		AutoRetry:                   true,
		MaxRetries:                  10,
		RetryDelaySeconds:           30,
		NetworkCheckIntervalSeconds: 10,
		AutoStartOnBoot:             false,
	}
}

type ConfigStore struct {
	mu     sync.RWMutex
	path   string
	config Config
}

func NewConfigStore() (*ConfigStore, error) {
	base, err := appDataDir()
	if err != nil {
		return nil, err
	}
	if err := os.MkdirAll(base, 0o755); err != nil {
		return nil, err
	}
	cfgPath := filepath.Join(base, "config.json")
	store := &ConfigStore{path: cfgPath, config: DefaultConfig()}
	if err := store.loadOrCreate(); err != nil {
		return nil, err
	}
	return store, nil
}

func (c *ConfigStore) loadOrCreate() error {
	b, err := os.ReadFile(c.path)
	if errors.Is(err, os.ErrNotExist) {
		return c.Save(DefaultConfig())
	}
	if err != nil {
		return err
	}
	cfg := DefaultConfig()
	if err := json.Unmarshal(b, &cfg); err != nil {
		return err
	}
	c.config = normalizeConfig(cfg)
	return nil
}

func (c *ConfigStore) Get() Config {
	c.mu.RLock()
	defer c.mu.RUnlock()
	return c.config
}

func (c *ConfigStore) Save(cfg Config) error {
	c.mu.Lock()
	defer c.mu.Unlock()
	cfg = normalizeConfig(cfg)
	b, err := json.MarshalIndent(cfg, "", "  ")
	if err != nil {
		return err
	}
	if err := os.WriteFile(c.path, b, 0o644); err != nil {
		return err
	}
	c.config = cfg
	return nil
}

func normalizeConfig(cfg Config) Config {
	def := DefaultConfig()
	if cfg.ListenPort <= 0 {
		cfg.ListenPort = def.ListenPort
	}
	if cfg.ChunkSizeMb <= 0 {
		cfg.ChunkSizeMb = def.ChunkSizeMb
	}
	if cfg.MaxConcurrent <= 0 {
		cfg.MaxConcurrent = def.MaxConcurrent
	}
	if cfg.MaxRetries <= 0 {
		cfg.MaxRetries = def.MaxRetries
	}
	if cfg.RetryDelaySeconds <= 0 {
		cfg.RetryDelaySeconds = def.RetryDelaySeconds
	}
	if cfg.NetworkCheckIntervalSeconds <= 0 {
		cfg.NetworkCheckIntervalSeconds = def.NetworkCheckIntervalSeconds
	}
	if cfg.ServerURL == "" {
		cfg.ServerURL = def.ServerURL
	}
	return cfg
}

func appDataDir() (string, error) {
	home, err := os.UserHomeDir()
	if err != nil {
		return "", err
	}
	switch runtime.GOOS {
	case "windows":
		appData := os.Getenv("APPDATA")
		if appData == "" {
			return filepath.Join(home, "AppData", "Roaming", "indygestion-agent"), nil
		}
		return filepath.Join(appData, "indygestion-agent"), nil
	case "darwin":
		return filepath.Join(home, "Library", "Application Support", "indygestion-agent"), nil
	default:
		return filepath.Join(home, ".local", "share", "indygestion-agent"), nil
	}
}

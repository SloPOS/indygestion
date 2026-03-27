package main

import "github.com/gen2brain/beeep"

type Notifier struct{}

func NewNotifier() *Notifier { return &Notifier{} }

func (n *Notifier) UploadComplete(filename string) {
	_ = beeep.Notify("Indygestion Upload Complete", filename, "")
}

func (n *Notifier) UploadFailed(filename, errMsg string) {
	_ = beeep.Notify("Indygestion Upload Failed", filename+" - "+errMsg, "")
}

func (n *Notifier) NetworkDisconnected() {
	_ = beeep.Notify("Indygestion", "Network disconnected - uploads paused", "")
}

func (n *Notifier) NetworkRestored() {
	_ = beeep.Notify("Indygestion", "Network restored - resuming uploads", "")
}

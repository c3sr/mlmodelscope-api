package models

import (
	"time"
)

type Framework struct {
	ID            uint           `gorm:"primaryKey" json:"id"`
	CreatedAt     time.Time      `json:"-"`
	UpdatedAt     time.Time      `json:"-"`
	Name          string         `json:"name"`
	Version       string         `json:"version"`
	Architectures []Architecture `json:"architectures"`
}

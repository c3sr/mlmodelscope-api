package db

import "api/db/models"

type ModelInteractor interface {
	CreateModel(*models.Model) error
	GetAllModels() ([]models.Model, error)
	GetModelsByTask(string) ([]models.Model, error)
	GetModelsForFramework(int) ([]models.Model, error)
}

func (d *Db) CreateModel(m *models.Model) (err error) {
	d.database.Create(m)

	return
}

func (d *Db) GetAllModels() (m []models.Model, err error) {
	d.database.Joins("Framework").Find(&m)

	return
}

func (d *Db) GetModelsByTask(task string) (m []models.Model, err error) {
	d.database.Where(&models.Model{Output: models.ModelOutput{Type: task}}).Joins("Framework").Find(&m)

	return
}

func (d *Db) GetModelsForFramework(frameworkId int) (m []models.Model, err error) {
	d.database.Where(&models.Model{FrameworkID: frameworkId}).Joins("Framework").Find(&m)

	return
}

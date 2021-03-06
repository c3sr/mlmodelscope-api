// +build !integration

package db

import (
	"api/db/models"
	"github.com/stretchr/testify/assert"
	"testing"
	"time"
)

func TestTrialInteractor(t *testing.T) {
	CreateTestDatabase()
	defer cleanupTestDatabase()

	createModelNamed("TestModel")
	testDb.CreateUser(&models.User{ID: "testUser"})
	testDb.CreateExperiment(&models.Experiment{ID: "experiment1", UserID: "testUser"})

	t.Run("CannotCreateTrialWithEmptyId", func(t *testing.T) {
		trial := models.Trial{}
		err := testDb.CreateTrial(&trial)

		assert.NotNil(t, err)
		assert.Equal(t, "attempt to create Trial without an ID", err.Error())
	})

	t.Run("CannotCreateTrialWithoutModel", func(t *testing.T) {
		trial := models.Trial{
			ID: "trial1",
		}
		err := testDb.CreateTrial(&trial)

		assert.NotNil(t, err)
		assert.Equal(t, "attempt to create Trial without an associated Model", err.Error())
	})

	t.Run("CannotCreateTrialWithoutExperiment", func(t *testing.T) {
		trial := models.Trial{
			ID:      "trial1",
			ModelID: 1,
		}
		err := testDb.CreateTrial(&trial)

		assert.NotNil(t, err)
		assert.Equal(t, "attempt to create Trial without an associated Experiment", err.Error())
	})

	t.Run("CreateAndQueryTrial", func(t *testing.T) {
		trial := models.Trial{
			ID:           "trial1",
			ModelID:      1,
			ExperimentID: "experiment1",
		}
		err := testDb.CreateTrial(&trial)

		assert.Nil(t, err)

		trials, err := testDb.GetAllTrials()

		assert.Nil(t, err)
		assert.Equal(t, 1, len(trials))
		assert.Equal(t, "trial1", trials[0].ID)
		assert.Equal(t, uint(1), trials[0].Model.ID)
		assert.Equal(t, "experiment1", trials[0].ExperimentID)
		assert.Nil(t, trials[0].CompletedAt)
		assert.Equal(t, "", trials[0].Result)
	})

	t.Run("CreateAndQueryTrialWithInput", func(t *testing.T) {
		trial := models.Trial{
			ID: "trial2",
			Inputs: []models.TrialInput{
				models.TrialInput{
					URL:    "testURL",
					UserID: "testUser",
				},
			},
			ModelID:      1,
			ExperimentID: "experiment1",
		}
		err := testDb.CreateTrial(&trial)

		assert.Nil(t, err)

		trials, err := testDb.GetAllTrials()

		assert.Nil(t, err)
		assert.Equal(t, "trial2", trials[1].ID)
		assert.Equal(t, 1, len(trials[1].Inputs))
		assert.Equal(t, "testUser", trials[1].Inputs[0].UserID)
	})

	t.Run("QueryTrialById", func(t *testing.T) {
		trial, err := testDb.GetTrialById("trial2")

		assert.NotNil(t, trial)
		assert.Nil(t, err)
		assert.Equal(t, "trial2", trial.ID)
		assert.Equal(t, 1, len(trial.Inputs))
	})

	t.Run("QueryMissingTrialById", func(t *testing.T) {
		_, err := testDb.GetTrialById("trial3")

		assert.NotNil(t, err)
		assert.Equal(t, "unknown Trial: trial3", err.Error())
	})

	t.Run("CompleteTrial", func(t *testing.T) {
		trial, _ := testDb.GetTrialById("trial2")
		err := testDb.CompleteTrial(trial, "trial_results")

		assert.Nil(t, err)

		complete, _ := testDb.GetTrialById("trial2")

		assert.NotNil(t, complete.CompletedAt)
		assert.NotEqual(t, time.Time{}, complete.CompletedAt)
		assert.Equal(t, "trial_results", complete.Result)
	})

	t.Run("CreateAndQueryTrialWithExperiment", func(t *testing.T) {
		testDb.CreateTrial(&models.Trial{ID: "trial4", ExperimentID: "experiment1", ModelID: 1})

		trial, _ := testDb.GetTrialById("trial4")

		assert.Equal(t, "experiment1", trial.Experiment.ID)
		assert.Equal(t, "testUser", trial.Experiment.UserID)
	})

	t.Run("CannotDeleteOnlyTrialInExperiment", func(t *testing.T) {
		testDb.CreateExperiment(&models.Experiment{ID: "deletion", UserID: "testUser"})
		testDb.CreateTrial(&models.Trial{ID: "trial5", ExperimentID: "deletion", ModelID: 1})

		err := testDb.DeleteTrial("trial5")

		assert.NotNil(t, err)
		assert.Equal(t, "DeleteTrial: Experiment must have at least one Trial", err.Error())
	})

	t.Run("CanDeleteTrialFromExperiment", func(t *testing.T) {
		testDb.CreateTrial(&models.Trial{ID: "trial6", ExperimentID: "deletion", ModelID: 1})

		err := testDb.DeleteTrial("trial5")

		assert.Nil(t, err)

		trial, err := testDb.GetTrialById("trial5")

		assert.NotNil(t, err)
		assert.Nil(t, trial)
	})

	t.Run("FindTrialByModelAndInputUrl", func(t *testing.T) {
		now := time.Now()
		testDb.CreateTrial(&models.Trial{
			ID:           "trial7",
			ExperimentID: "caching",
			ModelID:      1,
			Inputs: []models.TrialInput{
				{URL: "cached_input"},
			},
			CompletedAt: &now,
		})

		trial, err := testDb.GetTrialByModelAndInput(1, "cached_input")

		assert.Nil(t, err)
		assert.NotNil(t, trial)
		assert.Equal(t, "trial7", trial.ID)
	})

	t.Run("QueryTrialByIdReturnsSourceTrialResults", func(t *testing.T) {
		now := time.Now()
		testDb.CreateTrial(&models.Trial{
			ID:            "trial8",
			ExperimentID:  "source_trial",
			ModelID:       1,
			SourceTrialID: "trial2",
			CompletedAt:   &now,
		})

		trial, err := testDb.GetTrialById("trial8")

		assert.Nil(t, err)
		assert.NotNil(t, trial)
		assert.Equal(t, "trial8", trial.ID)
		assert.Equal(t, "source_trial", trial.ExperimentID)
		assert.Equal(t, "trial_results", trial.Result)
	})
}

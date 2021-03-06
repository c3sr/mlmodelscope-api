// +build !integration

package endpoints

import (
	"api/db/models"
	"encoding/json"
	"github.com/stretchr/testify/assert"
	"net/http"
	"net/http/httptest"
	"testing"
)

func TestTrialRoute(t *testing.T) {
	openDatabase()
	createTestModelAndFramework()
	createTestExperiment()
	defer cleanupTestDatabase()
	router := SetupRoutes()

	t.Run("GetTrialWithoutId", func(t *testing.T) {
		w := httptest.NewRecorder()
		req, _ := http.NewRequest("GET", "/trial/", nil)
		router.ServeHTTP(w, req)

		assert.Equal(t, 404, w.Code)
	})

	t.Run("GetTrialWithUnknownId", func(t *testing.T) {
		w := httptest.NewRecorder()
		req, _ := http.NewRequest("GET", "/trial/does_not_exist", nil)
		router.ServeHTTP(w, req)

		assert.Equal(t, 404, w.Code)
	})

	t.Run("GetIncompleteTrial", func(t *testing.T) {
		testDb.CreateTrial(&models.Trial{
			ID:           "trial1",
			ModelID:      1,
			ExperimentID: "test",
			Inputs: []models.TrialInput{
				models.TrialInput{
					URL: "test_url",
				},
			},
		})

		w := httptest.NewRecorder()
		req, _ := http.NewRequest("GET", "/trial/trial1", nil)
		router.ServeHTTP(w, req)

		assert.Equal(t, 200, w.Code)

		var trial trialResponse
		json.Unmarshal(w.Body.Bytes(), &trial)

		assert.Equal(t, "trial1", trial.ID)
		assert.Equal(t, "test_url", trial.Inputs[0])
		assert.Equal(t, uint(1), trial.Model.ID)
		assert.Nil(t, trial.CompletedAt)
	})

	t.Run("GetCompletedTrial", func(t *testing.T) {
		testDb.CreateTrial(&models.Trial{
			ID:           "trial2",
			ModelID:      1,
			ExperimentID: "test",
			Inputs: []models.TrialInput{
				models.TrialInput{
					URL: "test_url",
				},
			},
		})
		trial, _ := testDb.GetTrialById("trial2")
		testDb.CompleteTrial(trial, "{\"duration\": \"1s\", \"duration_for_inference\": \"0.5s\", \"responses\": [{\"features\": [{\"classification\":{\"index\": 933,\"label\":\"n07697313 cheeseburger\"},\"id\": \"61afb91c7cc38300018b8a74\",\"probability\": 0.64689136,\"type\": \"CLASSIFICATION\"}]}], \"trace_id\": {\"id\": \"trace\"}}")

		w := httptest.NewRecorder()
		req, _ := http.NewRequest("GET", "/trial/trial2", nil)
		router.ServeHTTP(w, req)

		assert.Equal(t, 200, w.Code)

		var response trialResponse
		json.Unmarshal(w.Body.Bytes(), &response)

		assert.Equal(t, "trial2", response.ID)
		assert.Equal(t, "test_url", response.Inputs[0])
		assert.Equal(t, uint(1), response.Model.ID)
		assert.Equal(t, uint(1), response.Model.Framework.ID)
		assert.True(t, response.CompletedAt.Equal(*trial.CompletedAt))
		assert.Equal(t, "1s", response.Results.Duration)
		assert.Equal(t, "0.5s", response.Results.DurationForInference)
		assert.Equal(t, 1, len(response.Results.Responses))
	})

	t.Run("DeleteOnlyTrialInExperiment", func(t *testing.T) {
		testDb.CreateExperiment(&models.Experiment{ID: "deletion", UserID: "experimentTestUser"})
		testDb.CreateTrial(&models.Trial{ID: "delete1", ExperimentID: "deletion", ModelID: 1})

		w := httptest.NewRecorder()
		req, _ := http.NewRequest("DELETE", "/trial/delete1", nil)
		router.ServeHTTP(w, req)

		assert.Equal(t, 400, w.Code)
	})

	t.Run("DeleteTrialFromExperiment", func(t *testing.T) {
		testDb.CreateTrial(&models.Trial{ID: "delete2", ExperimentID: "deletion", ModelID: 1})

		w := httptest.NewRecorder()
		req, _ := http.NewRequest("DELETE", "/trial/delete1", nil)
		router.ServeHTTP(w, req)

		assert.Equal(t, 200, w.Code)
	})
}

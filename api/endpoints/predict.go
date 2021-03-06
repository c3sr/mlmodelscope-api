package endpoints

import (
	"api/api_db"
	"api/api_mq"
	"api/db/models"
	"encoding/json"
	"fmt"
	"github.com/c3sr/mq/messages"
	"github.com/gin-gonic/gin"
	"github.com/google/uuid"
	"os"
	"strconv"
	"strings"
	"time"
)

type predictRequestBody struct {
	Architecture          string   `json:"architecture,omitempty" binding:"required"`
	BatchSize             uint     `json:"batchSize,omitempty" binding:"required"`
	DesiredResultModality string   `json:"desiredResultModality,omitempty" binding:"required"`
	Inputs                []string `json:"inputs,omitempty" binding:"required"`
	Model                 uint     `json:"model,omitempty" binding:"required"`
	TraceLevel            string   `json:"traceLevel,omitempty" binding:"required"`
	Experiment            string   `json:"experiment,omitempty"`
}

type predictResponseBody struct {
	ExperimentId string `json:"experimentId,omitempty"`
	TrialId      string `json:"trialId,omitempty"`
}

func Predict(c *gin.Context) {
	userId := "anonymous"
	requestBody := &predictRequestBody{}
	err := c.Bind(requestBody)
	if err != nil {
		return
	}

	db, _ := api_db.GetDatabase()

	existingTrialId := lookupExistingTrial(requestBody.Model, requestBody.Inputs[0])

	var experimentId string
	if experimentId = requestBody.Experiment; experimentId == "" {
		experimentId = uuid.New().String()
		db.CreateExperiment(&models.Experiment{ID: experimentId, UserID: userId})
	}

	if existingTrialId != "" {
		trialId := uuid.New().String()
		now := time.Now()
		db.CreateTrial(&models.Trial{
			ID:            trialId,
			ExperimentID:  experimentId,
			ModelID:       requestBody.Model,
			SourceTrialID: existingTrialId,
			CompletedAt:   &now,
		})

		c.JSON(200, &predictResponseBody{ExperimentId: experimentId, TrialId: trialId})
		return
	}

	model, err := db.GetModelById(requestBody.Model)
	if err != nil {
		c.JSON(400, err)

		return
	}

	channelName := fmt.Sprintf("agent-%s-%s", strings.ToLower(model.Framework.Name), requestBody.Architecture)
	messageQueue := api_mq.GetMessageQueue()
	channel, _ := messageQueue.GetPublishChannel(channelName)
	message := makePredictMessage(requestBody, model)
	messageBytes, _ := json.Marshal(message)
	correlationId, _ := channel.SendMessage(string(messageBytes))

	var inputs []models.TrialInput
	for _, input := range requestBody.Inputs {
		inputs = append(inputs, models.TrialInput{
			URL:    input,
			UserID: userId,
		})
	}

	err = db.CreateTrial(&models.Trial{
		ID:           correlationId,
		ExperimentID: experimentId,
		ModelID:      model.ID,
		Inputs:       inputs,
	})

	c.JSON(200, &predictResponseBody{ExperimentId: experimentId, TrialId: correlationId})
}

func lookupExistingTrial(modelId uint, input string) (trialId string) {
	db, _ := api_db.GetDatabase()
	trial, err := db.GetTrialByModelAndInput(modelId, input)

	if err != nil || trial == nil {
		return ""
	}

	return trial.ID
}

func makePredictMessage(request *predictRequestBody, model *models.Model) *messages.PredictByModelName {
	return &messages.PredictByModelName{
		BatchSize:             1,
		DesiredResultModality: request.DesiredResultModality,
		Inputs:                request.Inputs,
		ModelName:             fmt.Sprintf("%s_%s", strings.ToLower(model.Name), model.Version),
		Warmups:               getWarmups(),
		TraceLevel:            request.TraceLevel,
		TracerAddress:         getTracerAddress(),
		UseGpu:                false,
	}
}

func getTracerAddress() (address string) {
	if address = os.Getenv("TRACER_ADDRESS"); address == "" {
		address = "trace.mlmodelscope.org"
	}

	return
}

func getWarmups() uint {
	if warmups := os.Getenv("WARMUP_ROUNDS"); warmups == "" {
		return 0
	} else {
		num, err := strconv.ParseUint(warmups, 10, 32)
		if err != nil {
			return 0
		}

		return uint(num)
	}
}

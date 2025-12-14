package com.smartalarm.edge.ui.fx;

import com.smartalarm.edge.domain.FitbitPacket;
import com.smartalarm.edge.domain.SleepData;
import com.smartalarm.edge.service.AzureService;
import com.smartalarm.edge.service.CloudSyncService;
import com.smartalarm.edge.service.DataStorageService;
import com.smartalarm.edge.service.FitbitService;
import javafx.application.Platform;
import javafx.fxml.FXML;
import javafx.scene.control.Label;
import javafx.scene.control.TextArea;
import javafx.scene.layout.Region;

import java.util.concurrent.Executors;
import java.util.concurrent.ScheduledExecutorService;
import java.util.concurrent.TimeUnit;

public class SmartAlarmController {

    @FXML private TextArea logArea;
    @FXML private Label hrLabel;
    @FXML private Label hrvLabel;
    @FXML private Label stageLabel;
    @FXML private Label statusLabel;
    @FXML private Region statusIndicator;

    private ScheduledExecutorService scheduler;
    private FitbitService fitbitService;
    private LocalModelService modelService;
    private AzureService azureService;
    private DataStorageService storageService;
    private CloudSyncService cloudService;

    public void initialize() {
        initializeServices();
        startMonitoring();
    }

    private void initializeServices() {
        log("Initializing services...");
        fitbitService = new FitbitService();
        // Use environment variable for Model Service URL or fallback to Pi NodePort
        String modelUrl = System.getenv("MODEL_SERVICE_URL");
        if (modelUrl == null) modelUrl = "http://localhost:30000/predict";
        modelService = new LocalModelService(modelUrl);
        
        azureService = new AzureService(this::log);
        storageService = new DataStorageService();
        
        // Use environment variable for Cloud Service URL (Azure Container App)
        String cloudUrl = System.getenv("CLOUD_SERVICE_URL");
        if (cloudUrl == null) cloudUrl = "http://localhost:8080"; // Fallback for local dev
        cloudService = new CloudSyncService(cloudUrl);
        
        try {
            azureService.connect();
            log("Connected to Azure IoT Hub");
            updateStatus(true);
        } catch (Exception e) {
            log("Failed to connect to Azure: " + e.getMessage());
            updateStatus(false);
        }
    }

    @FXML
    private void handleSync() {
        log("Manual Sync triggered...");
        // Logic to force sync could go here
    }

    @FXML
    private void handleConfigUpdate() {
        log("Requesting Config Update...");
        // Logic to request twin update
    }

    private void startMonitoring() {
        scheduler = Executors.newSingleThreadScheduledExecutor();
        // Run every 30 seconds
        scheduler.scheduleAtFixedRate(this::processCycle, 0, 30, TimeUnit.SECONDS);
    }

    private void processCycle() {
        try {
            // 1. Fetch Data
            FitbitPacket packet = fitbitService.fetchLatestData();
            if (packet == null) {
                log("No new data from Fitbit.");
                return;
            }
            SleepData data = packet.sensorData();
            String fitbitLabel = packet.fitbitLabel();
            
            // Update UI Metrics
            Platform.runLater(() -> {
                hrLabel.setText(String.format("Heart Rate: %.1f bpm", data.heartRate()));
                hrvLabel.setText(String.format("HRV (SDNN): %.1f ms", data.sdnn()));
            });
            
            // 2. Store Raw Data
            storageService.storeRaw(data);
            
            // 3. Predict Sleep Stage
            String stage = modelService.predict(data);
            Platform.runLater(() -> stageLabel.setText("Sleep Stage: " + stage));
            
            log(String.format("Analysis: Local Model=[%s] vs Fitbit API=[%s]", stage, fitbitLabel));
            
            // 4. Check Alarm
            checkAlarm(stage);
            
            // 5. Send Telemetry
            azureService.sendTelemetry(data, stage);
            
            // 6. Cloud Analysis
            String cloudReport = cloudService.analyzeInCloud(data);
            log("Cloud Report: " + cloudReport);
            
        } catch (Exception e) {
            log("Error in process cycle: " + e.getMessage());
            e.printStackTrace();
        }
    }
    
    private void updateStatus(boolean connected) {
        Platform.runLater(() -> {
            if (connected) {
                statusLabel.setText("Connected");
                statusIndicator.getStyleClass().remove("status-disconnected");
                statusIndicator.getStyleClass().add("status-connected");
            } else {
                statusLabel.setText("Disconnected");
                statusIndicator.getStyleClass().remove("status-connected");
                statusIndicator.getStyleClass().add("status-disconnected");
            }
        });
    }
    
    private void checkAlarm(String stage) {
        if ("LIGHT".equals(stage) || "WAKE".equals(stage)) {
            log("ALARM TRIGGERED! (Condition met)");
        }
    }

    private void log(String message) {
        if (logArea != null) {
            Platform.runLater(() -> logArea.appendText(message + "\n"));
        } else {
            System.out.println(message);
        }
    }

    public void stop() {
        if (scheduler != null) scheduler.shutdown();
        try {
            if (azureService != null) azureService.close();
        } catch (Exception e) {
            e.printStackTrace();
        }
    }
}

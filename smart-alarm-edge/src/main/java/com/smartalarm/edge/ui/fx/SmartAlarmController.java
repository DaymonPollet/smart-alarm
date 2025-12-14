package com.smartalarm.edge.ui.fx;

import com.smartalarm.edge.domain.FitbitPacket;
import com.smartalarm.edge.domain.SleepData;
import com.smartalarm.edge.service.AzureService;
import com.smartalarm.edge.service.CloudSyncService;
import com.smartalarm.edge.service.DataStorageService;
import com.smartalarm.edge.service.FitbitService;
import com.smartalarm.edge.service.LocalModelService;
import javafx.application.Platform;
import javafx.fxml.FXML;
import javafx.scene.control.TextArea;

import java.util.concurrent.Executors;
import java.util.concurrent.ScheduledExecutorService;
import java.util.concurrent.TimeUnit;

public class SmartAlarmController {

    @FXML
    private TextArea logArea;

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
        modelService = new LocalModelService("http://localhost:30000/predict"); // K8s NodePort
        azureService = new AzureService(this::log);
        storageService = new DataStorageService();
        cloudService = new CloudSyncService("http://localhost:8080");
        
        try {
            azureService.connect();
            log("Connected to Azure IoT Hub");
        } catch (Exception e) {
            log("Failed to connect to Azure: " + e.getMessage());
        }
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
            
            // 2. Store Raw Data
            storageService.storeRaw(data);
            
            // 3. Predict Sleep Stage
            String stage = modelService.predict(data);
            log(String.format("Analysis: Local Model=[%s] vs Fitbit API=[%s]", stage, fitbitLabel));
            log(String.format("Metrics: HR=%.1f, HRV=%.1f, Activity=%.2f", data.heartRate(), data.sdnn(), data.meanActivity()));
            
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

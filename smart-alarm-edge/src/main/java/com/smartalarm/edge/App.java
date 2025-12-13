package com.smartalarm.edge;

import com.smartalarm.edge.model.SleepData;
import com.smartalarm.edge.service.AzureService;
import com.smartalarm.edge.service.DataStorageService;
import com.smartalarm.edge.service.FitbitService;
import com.smartalarm.edge.service.LocalModelService;
import javafx.application.Application;
import javafx.application.Platform;
import javafx.scene.Scene;
import javafx.scene.control.Label;
import javafx.scene.control.TextArea;
import javafx.scene.layout.VBox;
import javafx.stage.Stage;

import java.util.concurrent.Executors;
import java.util.concurrent.ScheduledExecutorService;
import java.util.concurrent.TimeUnit;

public class App extends Application {

    private TextArea logArea;
    private ScheduledExecutorService scheduler;
    private FitbitService fitbitService;
    private LocalModelService modelService;
    private AzureService azureService;
    private DataStorageService storageService;

    @Override
    public void start(Stage stage) {
        logArea = new TextArea();
        logArea.setEditable(false);
        
        VBox root = new VBox(new Label("Smart Alarm Edge Log"), logArea);
        Scene scene = new Scene(root, 600, 400);
        
        stage.setTitle("Smart Alarm Edge");
        stage.setScene(scene);
        stage.show();
        
        initializeServices();
        startMonitoring();
    }

    private void initializeServices() {
        log("Initializing services...");
        fitbitService = new FitbitService();
        modelService = new LocalModelService("http://localhost:30000/predict"); // K8s NodePort
        azureService = new AzureService(this::log);
        storageService = new DataStorageService();
        
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
            SleepData data = fitbitService.fetchLatestData();
            if (data == null) {
                log("No new data from Fitbit.");
                return;
            }
            
            // 2. Store Raw Data
            storageService.storeRaw(data);
            
            // 3. Predict Sleep Stage
            String stage = modelService.predict(data);
            log("Predicted Stage: " + stage);
            
            // 4. Check Alarm
            checkAlarm(stage);
            
            // 5. Send Telemetry
            azureService.sendTelemetry(data, stage);
            
        } catch (Exception e) {
            log("Error in process cycle: " + e.getMessage());
            e.printStackTrace();
        }
    }
    
    private void checkAlarm(String stage) {
        // Simple logic: If in LIGHT or WAKE and within time window (mocked), trigger alarm
        // In real app, check current time vs alarm time
        if ("LIGHT".equals(stage) || "WAKE".equals(stage)) {
            log("ALARM TRIGGERED! (Condition met)");
        }
    }

    private void log(String message) {
        Platform.runLater(() -> logArea.appendText(message + "\n"));
    }

    @Override
    public void stop() throws Exception {
        if (scheduler != null) scheduler.shutdown();
        if (azureService != null) azureService.close();
        super.stop();
    }

    public static void main(String[] args) {
        launch();
    }
}

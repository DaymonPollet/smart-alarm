package com.smartalarm.edge.service;

import com.smartalarm.edge.AppContext;
import com.smartalarm.edge.domain.FitbitPacket;
import com.smartalarm.edge.domain.SleepData;

import java.util.concurrent.Executors;
import java.util.concurrent.ScheduledExecutorService;
import java.util.concurrent.TimeUnit;
import java.util.function.Consumer;

public class MonitoringService {
    private final ScheduledExecutorService scheduler = Executors.newSingleThreadScheduledExecutor();
    private final AppContext ctx;
    private final Consumer<String> logger;

    public MonitoringService(Consumer<String> logger) {
        this.ctx = AppContext.getInstance();
        this.logger = logger;
    }

    public void start() {
        // Run every 60 seconds
        scheduler.scheduleAtFixedRate(this::processCycle, 0, 60, TimeUnit.SECONDS);
        logger.accept("Monitoring started.");
    }

    public void stop() {
        scheduler.shutdown();
    }

    private void processCycle() {
        try {
            // 1. Fetch Data
            FitbitPacket packet = ctx.getFitbitService().fetchLatestData();
            if (packet == null) return; // No data or API disabled/daytime

            // 2. Convert to SleepData (Feature Extraction)
            SleepData data = SleepData.fromPacket(packet);
            
            // 3. Local Prediction
            String prediction = ctx.getLocalModelService().predict(data);
            logger.accept("Local Prediction: " + prediction);
            
            // 4. Store Locally
            ctx.getDataStorageService().save(data, prediction);
            
            // 5. Send to Cloud (Azure IoT Hub)
            ctx.getAzureService().sendTelemetry(data, prediction);
            
            // 6. Sync with Cloud Service (Optional, if we want to compare models)
            // ctx.getCloudSyncService().sync(data);

        } catch (Exception e) {
            logger.accept("Error in monitoring cycle: " + e.getMessage());
            e.printStackTrace();
        }
    }
}

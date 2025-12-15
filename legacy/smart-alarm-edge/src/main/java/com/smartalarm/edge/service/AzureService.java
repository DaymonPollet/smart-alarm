package com.smartalarm.edge.service;

import com.microsoft.azure.sdk.iot.device.exceptions.IotHubClientException;
import com.smartalarm.edge.domain.SleepData;
import com.microsoft.azure.sdk.iot.device.*;
import com.microsoft.azure.sdk.iot.device.twin.*;
import com.fasterxml.jackson.databind.ObjectMapper;

import java.io.IOException;
import java.net.URISyntaxException;
import java.util.function.Consumer;

public class AzureService {
    private String connectionString;
    private DeviceClient client;
    private final Consumer<String> logger;
    private final ObjectMapper objectMapper = new ObjectMapper();

    public AzureService(Consumer<String> logger) {
        this.logger = logger;
        // Load from Environment Variable
        // Note: In .env, IOTHUB_CONNECTION_STRING contains the DeviceId=RPISmartHome part
        this.connectionString = System.getenv("IOTHUB_CONNECTION_STRING");
        if (this.connectionString == null || this.connectionString.isEmpty()) {
            logger.accept("ERROR: IOTHUB_CONNECTION_STRING not set in environment variables.");
            throw new RuntimeException("IOTHUB_CONNECTION_STRING is required.");
        }
    }

    public void connect() throws IOException, URISyntaxException {
        client = new DeviceClient(connectionString, IotHubClientProtocol.MQTT);
        try {
            client.open(true);
        } catch (IotHubClientException e) {
            throw new RuntimeException(e);
        }

        // Subscribe to Desired Properties updates
        client.subscribeToTwin(new TwinStatusCallBack(), null);
        client.startDeviceTwin(new DeviceTwinStatusCallBack(), null, new PropertyCallBack(), null);
    }

    public void sendTelemetry(SleepData data, String prediction) {
        if (client == null) return;

        try {
            String msgStr = objectMapper.writeValueAsString(new TelemetryData(data, prediction));
            Message msg = new Message(msgStr);
            client.sendEventAsync(msg, new EventCallback(), null);
        } catch (Exception e) {
            logger.accept("Error sending telemetry: " + e.getMessage());
        }
    }
    
    public void close() throws IOException {
        if (client != null) client.closeNow();
    }

    // Inner classes for callbacks
    
    private class EventCallback implements IotHubEventCallback {
        @Override
        public void execute(IotHubStatusCode status, Object context) {
            logger.accept("IoT Hub responded to message with status: " + status.name());
        }
    }

    private class TwinStatusCallBack implements IotHubEventCallback {
        @Override
        public void execute(IotHubStatusCode status, Object context) {
            logger.accept("Twin status: " + status.name());
        }
    }
    
    private class DeviceTwinStatusCallBack implements IotHubEventCallback {
        @Override
        public void execute(IotHubStatusCode status, Object context) {
            logger.accept("Device Twin Status: " + status.name());
        }
    }

    private class PropertyCallBack implements TwinPropertyCallBack {
        @Override
        public void TwinPropertyCallBack(Property property, Object context) {
            logger.accept("Property Changed: " + property.getKey() + " = " + property.getValue());
            
            try {
                if ("alarm_time".equals(property.getKey())) {
                    String newTime = (String) property.getValue();
                    logger.accept("Updating Alarm Time to: " + newTime);
                    // In a real app, we would update a Configuration singleton or notify the Controller
                    reportProperty("alarm_time", newTime);
                } else if ("smart_wakeup_window".equals(property.getKey())) {
                    int window = (int) property.getValue();
                    logger.accept("Updating Wakeup Window to: " + window);
                    reportProperty("smart_wakeup_window", window);
                } else if ("cloud_service_url".equals(property.getKey())) {
                    String url = (String) property.getValue();
                    logger.accept("Updating Cloud Service URL to: " + url);
                    // Notify controller or update singleton
                    reportProperty("cloud_service_url", url);
                }
            } catch (Exception e) {
                logger.accept("Failed to handle property update: " + e.getMessage());
            }
        }
    }

    public void reportProperty(String key, Object value) {
        try {
            TwinCollection reportedProperties = new TwinCollection();
            reportedProperties.put(key, value);
            client.updateReportedPropertiesAsync(reportedProperties, new ReportedPropertiesCallback(), null);
        } catch (Exception e) {
            logger.accept("Failed to report property: " + e.getMessage());
        }
    }

    private class ReportedPropertiesCallback implements IotHubEventCallback {
        @Override
        public void execute(IotHubStatusCode status, Object context) {
            logger.accept("Reported properties update status: " + status.name());
        }
    }
    
    private static class TelemetryData {
        public SleepData sleepData;
        public String prediction;
        
        public TelemetryData(SleepData data, String prediction) {
            this.sleepData = data;
            this.prediction = prediction;
        }
    }
}

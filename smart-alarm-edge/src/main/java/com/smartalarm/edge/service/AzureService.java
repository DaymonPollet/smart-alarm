package com.smartalarm.edge.service;

import com.smartalarm.edge.model.SleepData;
import com.microsoft.azure.sdk.iot.device.*;
import com.microsoft.azure.sdk.iot.device.twin.*;
import com.fasterxml.jackson.databind.ObjectMapper;

import java.io.IOException;
import java.net.URISyntaxException;
import java.util.HashSet;
import java.util.Set;
import java.util.function.Consumer;

public class AzureService {
    // TODO: Load from env or config
    private static final String CONN_STRING = "HostName=your-hub.azure-devices.net;DeviceId=your-device;SharedAccessKey=your-key";
    private DeviceClient client;
    private final Consumer<String> logger;
    private final ObjectMapper objectMapper = new ObjectMapper();

    public AzureService(Consumer<String> logger) {
        this.logger = logger;
    }

    public void connect() throws IOException, URISyntaxException {
        client = new DeviceClient(CONN_STRING, IotHubClientProtocol.MQTT);
        client.open();
        
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
            // TODO: Handle configuration changes (e.g., wake window)
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

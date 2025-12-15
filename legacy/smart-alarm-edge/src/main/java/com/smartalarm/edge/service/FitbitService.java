package com.smartalarm.edge.service;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.smartalarm.edge.domain.FitbitPacket;
import com.smartalarm.edge.domain.SleepData;
import org.apache.hc.client5.http.classic.methods.HttpGet;
import org.apache.hc.client5.http.impl.classic.CloseableHttpClient;
import org.apache.hc.client5.http.impl.classic.CloseableHttpResponse;
import org.apache.hc.client5.http.impl.classic.HttpClients;
import org.apache.hc.core5.http.io.entity.EntityUtils;

import java.time.LocalDate;
import java.util.ArrayList;
import java.util.List;
import java.util.Random;

public class FitbitService {
    private static final String API_BASE = "https://api.fitbit.com";
    private final ObjectMapper mapper = new ObjectMapper();
    private final String accessToken;
    private boolean enabled;
    private final Random random = new Random();

    public FitbitService() {
        // load env vars
        this.accessToken = System.getenv("FITBIT_ACCESS_TOKEN");
        String enableStr = System.getenv("ENABLE_FITBIT_API");
        // default false cuz i want to turn it on manually
        this.enabled = "true".equalsIgnoreCase(enableStr);
        
        if (this.enabled && (this.accessToken == null || this.accessToken.isEmpty())) {
            System.err.println("WARNING: ENABLE_FITBIT_API is true but FITBIT_ACCESS_TOKEN is missing.");
        }
    }

    public void setEnabled(boolean enabled) {
        this.enabled = enabled;
    }

    public boolean isEnabled() {
        return enabled;
    }

    public FitbitPacket fetchLatestData() {
        // Check time: Only query between 22:00 and 08:00
        LocalTime now = LocalTime.now();
        boolean isNight = now.isAfter(LocalTime.of(22, 0)) || now.isBefore(LocalTime.of(8, 0));

        if (!enabled || accessToken == null || !isNight) {
            if (enabled && !isNight) {
                System.out.println("Fitbit API enabled but it's daytime. Skipping API call.");
            }
            return fetchMockData();
        }

        try (CloseableHttpClient client = HttpClients.createDefault()) {
            String date = LocalDate.now().toString(); // YYYY-MM-DD
            
            // 1. Fetch Heart Rate (1sec resolution)
            // Endpoint: /1/user/-/activities/heart/date/[date]/1d/1sec.json
            String hrUrl = String.format("%s/1/user/-/activities/heart/date/%s/1d/1sec.json", API_BASE, date);
            JsonNode hrNode = fetch(client, hrUrl);
            
            // 2. Fetch Sleep Logs (for labels)
            String sleepUrl = String.format("%s/1.2/user/-/sleep/date/%s.json", API_BASE, date);
            JsonNode sleepNode = fetch(client, sleepUrl);
            
            // 3. Fetch Activity (Steps/Intensity)
            String actUrl = String.format("%s/1/user/-/activities/steps/date/%s/1d/1min.json", API_BASE, date);
            JsonNode actNode = fetch(client, actUrl);

            return processRealData(hrNode, sleepNode, actNode);

        } catch (Exception e) {
            System.err.println("Fitbit API Failed (Falling back to mock): " + e.getMessage());
            return fetchMockData();
        }
    }

    private JsonNode fetch(CloseableHttpClient client, String url) throws Exception {
        HttpGet request = new HttpGet(url);
        request.setHeader("Authorization", "Bearer " + accessToken);
        
        try (CloseableHttpResponse response = client.execute(request)) {
            if (response.getCode() != 200) {
                throw new RuntimeException("HTTP " + response.getCode());
            }
            String json = EntityUtils.toString(response.getEntity());
            return mapper.readTree(json);
        }
    }

    private FitbitPacket processRealData(JsonNode hrNode, JsonNode sleepNode, JsonNode actNode) {
        // 1. Parse Heart Rate Data (Intraday)
        List<Double> rrIntervals = new ArrayList<>();
        List<Integer> hrValues = new ArrayList<>();
        
        JsonNode hrDataset = hrNode.path("activities-heart-intraday").path("dataset");
        if (hrDataset.isArray()) {
            // get data for, last 60 seconds (approx 60 entries)
            int size = hrDataset.size();
            int start = Math.max(0, size - 60);
            
            for (int i = start; i < size; i++) {
                int hr = hrDataset.get(i).path("value").asInt();
                if (hr > 0) {
                    hrValues.add(hr);
                    rrIntervals.add(60000.0 / hr); // Convert BPM to RR interval in ms
                }
            }
        }

        if (hrValues.isEmpty()) {
            // No data available right now (e.g., device syncing delay), fallback to mock to keep app running
            System.out.println("No real HR data found in recent window. Using mock values.");
            return fetchMockData();
        }

        double meanHr = hrValues.stream().mapToInt(Integer::intValue).average().orElse(0.0);
        double minHr = hrValues.stream().mapToInt(Integer::intValue).min().orElse(0);
        double maxHr = hrValues.stream().mapToInt(Integer::intValue).max().orElse(0);
        
        // Calculate SDNN
        double meanRr = rrIntervals.stream().mapToDouble(Double::doubleValue).average().orElse(0.0);
        double sdnn = Math.sqrt(rrIntervals.stream().mapToDouble(rr -> Math.pow(rr - meanRr, 2)).average().orElse(0.0));

        // Calculate RMSSD
        double sumSquaredDiffs = 0.0;
        for (int i = 0; i < rrIntervals.size() - 1; i++) {
            double diff = rrIntervals.get(i + 1) - rrIntervals.get(i);
            sumSquaredDiffs += diff * diff;
        }
        double rmssd = (rrIntervals.size() > 1) ? Math.sqrt(sumSquaredDiffs / (rrIntervals.size() - 1)) : 0.0;

        // 2. Parse Activity Data
        double meanActivity = 0.0;
        double stdActivity = 0.0;
        JsonNode actDataset = actNode.path("activities-steps-intraday").path("dataset");
        if (actDataset.isArray()) {
             // Last 5 minutes
             int size = actDataset.size();
             int start = Math.max(0, size - 5);
             List<Double> steps = new ArrayList<>();
             for (int i = start; i < size; i++) {
                 steps.add(actDataset.get(i).path("value").asDouble());
             }
             meanActivity = steps.stream().mapToDouble(Double::doubleValue).average().orElse(0.0);
             
             double finalMeanActivity = meanActivity;
             stdActivity = Math.sqrt(steps.stream().mapToDouble(s -> Math.pow(s - finalMeanActivity, 2)).average().orElse(0.0));
        }

        // 3. Parse Sleep Label
        String label = "WAKE"; 
        // Check if we are in a sleep session
        if (sleepNode.has("sleep") && sleepNode.get("sleep").size() > 0) {
            // Simplified: If there is a sleep log for today, we assume we are tracking sleep.
            label = "ASLEEP"; 
        }

        SleepData data = new SleepData(meanHr, 0.0, sdnn, rmssd, minHr, maxHr, meanActivity, stdActivity);
        return new FitbitPacket(data, label);
    }

    private FitbitPacket fetchMockData() {
        // Mocking data to simulate the engineered features
        double meanHr = 60 + random.nextGaussian() * 5;
        
        // Simulate HRV (Standard Deviation of NN intervals - approximated by HR variance here for mock)
        double stdHr = 2 + random.nextDouble() * 5; 
        double sdnn = stdHr * 10; // Mock SDNN
        double rmssd = stdHr * 8; // Mock RMSSD
        
        double minHr = meanHr - 5;
        double maxHr = meanHr + 5;
        
        // Activity score (0 for sleep, higher for wake)
        double meanActivity = random.nextDouble() * 0.5; 
        double stdActivity = random.nextDouble() * 0.1;
        
        SleepData data = new SleepData(meanHr, stdHr, sdnn, rmssd, minHr, maxHr, meanActivity, stdActivity);
        
        // Mock Fitbit's own classification based on the data we just generated
        String label = "LIGHT";
        if (meanActivity > 0.3) label = "WAKE";
        else if (sdnn > 50) label = "DEEP";
        else if (meanHr > 70) label = "REM";
        
        return new FitbitPacket(data, label);
    }
}

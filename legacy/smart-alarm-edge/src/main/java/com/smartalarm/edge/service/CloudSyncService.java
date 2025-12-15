package com.smartalarm.edge.service;

import com.google.gson.JsonObject;
import com.smartalarm.edge.domain.SleepData;
import org.apache.hc.client5.http.classic.methods.HttpPost;
import org.apache.hc.client5.http.impl.classic.CloseableHttpClient;
import org.apache.hc.client5.http.impl.classic.CloseableHttpResponse;
import org.apache.hc.client5.http.impl.classic.HttpClients;
import org.apache.hc.core5.http.io.entity.StringEntity;
// import org.json.JSONObject; is unresolved by entelij editor

import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
import java.util.stream.Collectors;

public class CloudSyncService {

    private final String cloudUrl;

    public CloudSyncService(String cloudUrl) {
        this.cloudUrl = cloudUrl;
    }

    public String analyzeInCloud(SleepData data) {
        try (CloseableHttpClient httpClient = HttpClients.createDefault()) {
            HttpPost request = new HttpPost(cloudUrl + "/api/sleep/analyze");
            request.setHeader("Content-Type", "application/json");

            // Map SleepData (Edge) to SleepSession (Cloud) JSON structure
            JsonObject json = new JsonObject();
            json.addProperty("sessionId", System.currentTimeMillis()); // Generate a session ID
            json.addProperty("avgHr", data.heartRate());
            json.addProperty("avgHrv", data.sdnn()); // Using SDNN as proxy for avgHrv
            json.addProperty("deepSleepPercentage", 15.0); // Mocked for now, or calculated if we had history
            json.addProperty("remSleepPercentage", 20.0);
            json.addProperty("lightSleepPercentage", 65.0);
            json.addProperty("awakeCount", 1);

            request.setEntity(new StringEntity(json.toString(), StandardCharsets.UTF_8));

            try (CloseableHttpResponse response = httpClient.execute(request)) {
                if (response.getCode() == 200) {
                    return new BufferedReader(new InputStreamReader(response.getEntity().getContent()))
                            .lines().collect(Collectors.joining("\n"));
                } else {
                    return "Cloud Error: " + response.getCode();
                }
            }
        } catch (Exception e) {
            return "Cloud Connection Failed: " + e.getMessage();
        }
    }
}

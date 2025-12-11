package com.smartalarm.edge;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.smartalarm.shared.SleepData;

import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;

public class CloudClient {

    private final HttpClient httpClient;
    private final ObjectMapper objectMapper;
    private final String cloudUrl;

    public CloudClient() {
        this.httpClient = HttpClient.newHttpClient();
        this.objectMapper = new ObjectMapper();
        this.cloudUrl = "http://localhost:8080/api/sleep/analyze";
    }

    public String sendData(SleepData data) {
        try {
            String json = objectMapper.writeValueAsString(data);
            HttpRequest request = HttpRequest.newBuilder()
                    .uri(URI.create(cloudUrl))
                    .header("Content-Type", "application/json")
                    .POST(HttpRequest.BodyPublishers.ofString(json))
                    .build();

            HttpResponse<String> response = httpClient.send(request, HttpResponse.BodyHandlers.ofString());
            return response.body();
        } catch (Exception e) {
            return "ERROR";
        }
    }
}

package com.smartalarm.edge.service;

import com.smartalarm.edge.domain.SleepData;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.apache.hc.client5.http.classic.methods.HttpPost;
import org.apache.hc.client5.http.impl.classic.CloseableHttpClient;
import org.apache.hc.client5.http.impl.classic.CloseableHttpResponse;
import org.apache.hc.client5.http.impl.classic.HttpClients;
import org.apache.hc.core5.http.ContentType;
import org.apache.hc.core5.http.io.entity.StringEntity;

import java.io.IOException;
import java.util.HashMap;
import java.util.Map;

public class LocalModelService {
    private final String endpointUrl;
    private final ObjectMapper objectMapper;

    public LocalModelService(String endpointUrl) {
        this.endpointUrl = endpointUrl;
        this.objectMapper = new ObjectMapper();
    }

    public String predict(SleepData data) {
        try (CloseableHttpClient httpClient = HttpClients.createDefault()) {
            HttpPost request = new HttpPost(endpointUrl);
            
            Map<String, Double> payload = new HashMap<>();
            payload.put("mean_hr", data.meanHr());
            payload.put("std_hr", data.stdHr());
            payload.put("min_hr", data.minHr());
            payload.put("max_hr", data.maxHr());
            payload.put("mean_activity", data.meanActivity());
            payload.put("std_activity", data.stdActivity());
            
            String json = objectMapper.writeValueAsString(payload);
            request.setEntity(new StringEntity(json, ContentType.APPLICATION_JSON));
            
            try (CloseableHttpResponse response = httpClient.execute(request)) {
                if (response.getCode() == 200) {
                    JsonNode root = objectMapper.readTree(response.getEntity().getContent());
                    if (root.has("prediction")) {
                        return root.get("prediction").asText();
                    }
                }
            }
        } catch (IOException e) {
            System.err.println("Error calling model service: " + e.getMessage());
        }
        return "UNKNOWN";
    }
}

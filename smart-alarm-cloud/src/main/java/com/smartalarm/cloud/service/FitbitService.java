package com.smartalarm.cloud.service;

import com.smartalarm.shared.SleepData;
import lombok.RequiredArgsConstructor;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestClient;

import java.time.LocalDate;
import java.time.LocalDateTime;
import java.util.Map;

@Service
@RequiredArgsConstructor
public class FitbitService {

    @Value("${fitbit.client.id}")
    private String clientId;

    @Value("${fitbit.client.secret}")
    private String clientSecret;

    @Value("${fitbit.access.token}")
    private String accessToken;

    private final RestClient restClient = RestClient.builder()
            .baseUrl("https://api.fitbit.com")
            .build();

    public SleepData fetchSleepData() {
        String date = LocalDate.now().toString();
        
        var response = restClient.get()
                .uri("/1.2/user/-/sleep/date/{date}.json", date)
                .header(HttpHeaders.AUTHORIZATION, "Bearer " + accessToken)
                .accept(MediaType.APPLICATION_JSON)
                .retrieve()
                .body(Map.class);

        return parseFitbitResponse(response);
    }

    private SleepData parseFitbitResponse(Map<String, Object> response) {
        SleepData data = new SleepData();
        data.setTimestamp(LocalDateTime.now());
        data.setUserId(clientId);
        data.setHeartRate(70.0); 
        data.setMovementLevel(0.5);
        data.setSleepStage("LIGHT");
        return data;
    }
}

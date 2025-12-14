package com.smartalarm.cloud.controller;

import com.smartalarm.cloud.model.SleepSession;
import com.smartalarm.cloud.service.AnomalyDetectionService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/sleep")
public class SleepAnalysisController {

    private final AnomalyDetectionService anomalyService;

    @Autowired
    public SleepAnalysisController(AnomalyDetectionService anomalyService) {
        this.anomalyService = anomalyService;
    }

    @PostMapping("/analyze")
    public String analyzeSleepSession(@RequestBody SleepSession session) {
        System.out.println("Received sleep session for analysis: " + session);
        return anomalyService.analyze(session);
    }

    @GetMapping("/health")
    public String health() {
        return "Cloud Service is Running";
    }
}

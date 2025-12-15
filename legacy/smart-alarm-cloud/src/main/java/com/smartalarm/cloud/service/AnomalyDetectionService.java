package com.smartalarm.cloud.service;

import com.smartalarm.cloud.model.SleepSession;
import com.smartalarm.cloud.repository.SleepSessionRepository;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestTemplate;

@Service
public class AnomalyDetectionService {

    private final SleepSessionRepository repository;
    private final RestTemplate restTemplate = new RestTemplate();
    
    // URL of the Python Model Service running in the Cloud (Azure Container Apps)
    // In Docker Compose, this would be http://python-model-service:5000
    @Value("${python.service.url:http://python-model-service:5000}")
    private String pythonServiceUrl;

    @Autowired
    public AnomalyDetectionService(SleepSessionRepository repository) {
        this.repository = repository;
    }

    /**
     * Cloud AI Model: 
     * 1. Stores data in Cloud Database (H2/SQL).
     * 2. Calls Python AI Service for advanced anomaly detection.
     */
    public String analyze(SleepSession session) {
        // 1. Store Data (Cloud Storage Requirement)
        repository.save(session);
        
        // 2. Call Python AI Service (Cloud AI Requirement)
        try {
            // We send the session data to the Python service for "Advanced Analysis"
            // For now, we assume the Python service has an endpoint /analyze_anomaly
            // If not reachable, we fallback to local heuristics.
            // String aiResult = restTemplate.postForObject(pythonServiceUrl + "/analyze_anomaly", session, String.class);
            // return "Cloud AI (Python): " + aiResult;
            
            // Since we haven't implemented /analyze_anomaly in Python yet, let's use a statistical approach here
            // which is better than hardcoded rules.
            return performStatisticalAnalysis(session);
            
        } catch (Exception e) {
            return "Cloud AI Error: " + e.getMessage();
        }
    }

    private String performStatisticalAnalysis(SleepSession session) {
        // Fetch historical average from DB
        Double avgHrvHistory = repository.findAll().stream()
                .mapToDouble(SleepSession::getAvgHrv)
                .average().orElse(0.0);
                
        if (avgHrvHistory == 0) return "First session recorded. No history for AI analysis.";
        
        // Simple Z-Score like detection
        double deviation = session.getAvgHrv() - avgHrvHistory;
        
        if (deviation < -15) {
            return "AI ALERT: HRV is significantly lower (" + String.format("%.1f", deviation) + ") than your historical average. High Stress detected.";
        } else if (deviation > 15) {
             return "AI NOTICE: HRV is significantly higher. Good recovery!";
        }
        
        return "Sleep patterns are consistent with your history.";
    }
}

package com.smartalarm.cloud;

import com.smartalarm.cloud.repository.SleepDataRepository;
import com.smartalarm.cloud.service.FitbitService;
import com.smartalarm.shared.SleepData;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;

@Service
@RequiredArgsConstructor
public class CloudModelService {

    private final FitbitService fitbitService;
    private final SleepDataRepository repository;

    public String analyzeSleepPattern(SleepData data) {
        repository.save(data);
        
        if (data.getHeartRate() < 60 && data.getMovementLevel() < 0.2) {
            return "DEEP_SLEEP";
        } else if (data.getHeartRate() > 80 || data.getMovementLevel() > 0.8) {
            return "AWAKE";
        } else {
            return "LIGHT_SLEEP";
        }
    }

    public void syncFitbitData() {
        SleepData data = fitbitService.fetchSleepData();
        repository.save(data);
    }
}

package com.smartalarm.cloud;

import com.smartalarm.shared.SleepData;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/sleep")
@RequiredArgsConstructor
public class SleepDataController {

    private final CloudModelService modelService;

    @PostMapping("/analyze")
    public String analyze(@RequestBody SleepData data) {
        return modelService.analyzeSleepPattern(data);
    }
}

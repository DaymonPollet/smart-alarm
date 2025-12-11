package com.smartalarm.cloud.repository;

import com.smartalarm.shared.SleepData;
import lombok.RequiredArgsConstructor;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.stereotype.Repository;

@Repository
@RequiredArgsConstructor
public class SleepDataRepository {

    private final RedisTemplate<String, Object> redisTemplate;
    private static final String KEY_PREFIX = "sleep_data:";

    public void save(SleepData data) {
        String key = KEY_PREFIX + data.getUserId() + ":" + data.getTimestamp();
        redisTemplate.opsForValue().set(key, data);
    }

    public SleepData findLatest(String userId) {
        return (SleepData) redisTemplate.opsForValue().get(KEY_PREFIX + userId + ":latest");
    }
}

package com.smartalarm.cloud.repository;

import com.smartalarm.cloud.model.SleepSession;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

@Repository
public interface SleepSessionRepository extends JpaRepository<SleepSession, Long> {
}

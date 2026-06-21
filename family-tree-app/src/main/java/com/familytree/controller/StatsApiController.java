package com.familytree.controller;

import com.familytree.model.DashboardStats;
import com.familytree.model.TopAncestor;
import com.familytree.model.TopCensusAncestor;
import com.familytree.service.StatsService;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;

@RestController
@RequestMapping("/api/stats")
public class StatsApiController {

    private final StatsService statsService;

    public StatsApiController(StatsService statsService) {
        this.statsService = statsService;
    }

    @GetMapping
    public DashboardStats getStats() {
        return statsService.getDashboardStats();
    }

    @GetMapping("/top-ancestors")
    public List<TopAncestor> getTopAncestors() {
        return statsService.getTopAncestorsByDescendants();
    }

    @GetMapping("/top-census")
    public List<TopCensusAncestor> getTopByCensus() {
        return statsService.getTopAncestorsByCensus();
    }
}

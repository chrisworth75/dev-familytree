package com.familytree.controller;

import org.springframework.security.core.Authentication;
import org.springframework.security.oauth2.jwt.Jwt;
import org.springframework.security.oauth2.server.resource.authentication.JwtAuthenticationToken;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/me")
public class MeApiController {

    @GetMapping
    public Map<String, Object> me(Authentication authentication) {
        String subject = authentication.getName();

        if (authentication instanceof JwtAuthenticationToken jwtAuthentication) {
            Jwt token = jwtAuthentication.getToken();
            subject = token.getSubject();
        }

        List<String> authorities = authentication.getAuthorities().stream()
            .map(Object::toString)
            .sorted()
            .toList();

        Map<String, Object> response = new LinkedHashMap<>();
        response.put("username", authentication.getName());
        response.put("subject", subject);
        response.put("authorities", authorities);
        return response;
    }
}

package com.familytree.config;

import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.annotation.web.configuration.EnableWebSecurity;
import org.springframework.security.core.userdetails.User;
import org.springframework.security.core.userdetails.UserDetails;
import org.springframework.security.core.userdetails.UserDetailsService;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.security.provisioning.InMemoryUserDetailsManager;
import org.springframework.security.web.SecurityFilterChain;

@Configuration
@EnableWebSecurity
public class SecurityConfig {

    @Bean
    public SecurityFilterChain securityFilterChain(HttpSecurity http) throws Exception {
        http
            .authorizeHttpRequests(auth -> auth
                .requestMatchers("/css/**", "/js/**", "/images/**").permitAll()
                .requestMatchers("/login", "/error").permitAll()
                .anyRequest().authenticated()
            )
            .formLogin(form -> form
                .loginPage("/login")
                .defaultSuccessUrl("/", true)
                .permitAll()
            )
            .logout(logout -> logout
                .logoutSuccessUrl("/login?logout")
                .permitAll()
            );

        return http.build();
    }

    @Bean
    public PasswordEncoder passwordEncoder() {
        return new BCryptPasswordEncoder();
    }

    @Bean
    public UserDetailsService userDetailsService(PasswordEncoder encoder) {
        // TODO: Move to database or external config for production
        // For now, define family users here. Change passwords before deploying!

        UserDetails chris = User.builder()
            .username("chris")
            .password(encoder.encode("changeme"))  // CHANGE THIS
            .roles("USER", "ADMIN")
            .build();

        UserDetails familyAu = User.builder()
            .username("family-au")
            .password(encoder.encode("changeme"))  // CHANGE THIS
            .roles("USER")
            .build();

        UserDetails familyCa = User.builder()
            .username("family-ca")
            .password(encoder.encode("changeme"))  // CHANGE THIS
            .roles("USER")
            .build();

        UserDetails familyUk = User.builder()
            .username("family-uk")
            .password(encoder.encode("changeme"))  // CHANGE THIS
            .roles("USER")
            .build();

        return new InMemoryUserDetailsManager(chris, familyAu, familyCa, familyUk);
    }
}

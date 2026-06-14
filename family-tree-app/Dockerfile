# Multistage build for the Spring Boot API.
# Build context: family-tree-app/  (pom.xml + src/)
# Java 17 to match <java.version>17</java.version>.

# ---- build ----
FROM maven:3.9-eclipse-temurin-17 AS build
WORKDIR /build
# Cache dependencies first
COPY pom.xml .
RUN mvn -q -ntp dependency:go-offline
# Then the source; tests run in CI (Testcontainers needs Docker), not here
COPY src ./src
RUN mvn -q -ntp clean package -DskipTests

# ---- runtime ----
FROM eclipse-temurin:17-jre
WORKDIR /app
COPY --from=build /build/target/family-tree-app-*.jar app.jar
ENV SPRING_PROFILES_ACTIVE=k8s
EXPOSE 3200
ENTRYPOINT ["java", "-jar", "/app/app.jar"]

package com.gientech.raggateway;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.cloud.client.discovery.EnableDiscoveryClient;
import org.springframework.cloud.openfeign.EnableFeignClients;

@EnableFeignClients
@EnableDiscoveryClient
@SpringBootApplication(scanBasePackages = {"com.gientech.raggateway","com.gientech.start.redisson"})
public class RagGatewayApplication {

	public static void main(String[] args) {
		SpringApplication.run(RagGatewayApplication.class, args);
	}

}

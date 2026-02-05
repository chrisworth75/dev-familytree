package com.familytree.service;

import com.familytree.service.TreeDataService.TreeNode;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.MediaType;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestClient;
import org.springframework.web.client.RestClientException;

@Service
public class TreeRenderService {

    private final RestClient restClient;
    private final String renderUrl;

    public TreeRenderService(
            @Value("${d3.tree.service.url:http://localhost:3300}") String d3ServiceUrl) {
        this.restClient = RestClient.create();
        this.renderUrl = d3ServiceUrl + "/render";
    }

    /**
     * Render a tree node hierarchy as SVG using the D3 tree service.
     *
     * @param tree the tree node hierarchy to render
     * @return SVG content as bytes
     * @throws D3ServiceException if the D3 service is unavailable or returns an error
     */
    public byte[] renderToSvg(TreeNode tree) {
        try {
            return restClient.post()
                    .uri(renderUrl)
                    .contentType(MediaType.APPLICATION_JSON)
                    .body(tree)
                    .retrieve()
                    .body(byte[].class);
        } catch (RestClientException e) {
            throw new D3ServiceException("Failed to render tree: " + e.getMessage(), e);
        }
    }

    public static class D3ServiceException extends RuntimeException {
        public D3ServiceException(String message, Throwable cause) {
            super(message, cause);
        }
    }
}

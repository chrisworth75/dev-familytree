package com.familytree.controller;

import com.familytree.config.TreesConfig;
import com.familytree.model.FamilyTreeConfig;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.security.core.userdetails.UserDetails;
import org.springframework.stereotype.Controller;
import org.springframework.ui.Model;
import org.springframework.web.bind.annotation.GetMapping;

import java.util.List;

@Controller
public class HomeController {

    private final TreesConfig treesConfig;

    public HomeController(TreesConfig treesConfig) {
        this.treesConfig = treesConfig;
    }

    @GetMapping("/")
    public String home(@AuthenticationPrincipal UserDetails user, Model model) {
        List<FamilyTreeConfig> trees = treesConfig.getTreesForUser(user.getUsername());
        model.addAttribute("trees", trees);
        model.addAttribute("username", user.getUsername());
        return "home";
    }
}

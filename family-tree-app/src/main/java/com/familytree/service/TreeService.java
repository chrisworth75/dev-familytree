package com.familytree.service;

import com.familytree.model.Person;
import com.familytree.model.Tree;
import com.familytree.repository.PersonRepository;
import com.familytree.repository.TreeRepository;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;

import java.util.*;

@Service
public class TreeService {

    private final TreeRepository treeRepository;
    private final PersonRepository personRepository;
    private final JdbcTemplate jdbc;

    public TreeService(TreeRepository treeRepository,
                       PersonRepository personRepository,
                       JdbcTemplate jdbc) {
        this.treeRepository = treeRepository;
        this.personRepository = personRepository;
        this.jdbc = jdbc;
    }

    public List<Tree> getAllTrees() {
        return treeRepository.findAllWithMembers();
    }

    public Optional<Tree> getTree(Long id) {
        return treeRepository.findById(id);
    }

    public List<Person> getPersonsForTree(Long treeId) {
        return jdbc.query(
            "SELECT * FROM person WHERE tree_id = ? ORDER BY surname, first_name",
            (rs, rowNum) -> {
                java.sql.Date birthDate = rs.getDate("birth_date");
                java.sql.Date deathDate = rs.getDate("death_date");
                return new Person(
                    rs.getLong("id"),
                    rs.getString("first_name"),
                    rs.getString("middle_names"),
                    rs.getString("surname"),
                    birthDate != null ? birthDate.toLocalDate() : null,
                    (Integer) rs.getObject("birth_year_approx"),
                    rs.getString("birth_place"),
                    deathDate != null ? deathDate.toLocalDate() : null,
                    (Integer) rs.getObject("death_year_approx"),
                    rs.getString("death_place"),
                    rs.getString("gender"),
                    rs.getObject("father_id") != null ? rs.getLong("father_id") : null,
                    rs.getObject("mother_id") != null ? rs.getLong("mother_id") : null,
                    rs.getString("notes"),
                    (Integer) rs.getObject("tree_id"),
                    rs.getString("avatar_path")
                );
            },
            treeId
        );
    }

    public TreeData getTreeData(Long treeId) {
        Tree tree = treeRepository.findById(treeId).orElse(null);
        if (tree == null) {
            return new TreeData(List.of(), List.of());
        }

        // Get persons for this tree
        List<Person> persons = getPersonsForTree(treeId);

        // Build members list
        List<SvgMember> members = new ArrayList<>();
        for (Person p : persons) {
            members.add(new SvgMember(
                String.valueOf(p.id()),
                p.fullName(),
                p.birthYear(),
                p.deathYear()
            ));
        }

        // Build parent-child relationships for SVG
        List<SvgRelationship> svgRelationships = new ArrayList<>();
        for (Person p : persons) {
            String childId = String.valueOf(p.id());

            if (p.parent1Id() != null) {
                svgRelationships.add(new SvgRelationship("parent-child", String.valueOf(p.parent1Id()), childId));
            }
            if (p.parent2Id() != null) {
                svgRelationships.add(new SvgRelationship("parent-child", String.valueOf(p.parent2Id()), childId));
            }
        }

        return new TreeData(members, svgRelationships);
    }

    public record TreeData(List<SvgMember> members, List<SvgRelationship> relationships) {}

    public record SvgMember(String id, String name, Integer birthYear, Integer deathYear) {}

    public record SvgRelationship(String type, String parentId, String childId) {}
}

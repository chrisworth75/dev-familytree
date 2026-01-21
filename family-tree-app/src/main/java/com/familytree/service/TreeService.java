package com.familytree.service;

import com.familytree.model.Person;
import com.familytree.model.Tree;
import com.familytree.model.TreeRelationship;
import com.familytree.repository.PersonRepository;
import com.familytree.repository.TreeRelationshipRepository;
import com.familytree.repository.TreeRepository;
import org.springframework.stereotype.Service;

import java.util.*;

@Service
public class TreeService {

    private final TreeRepository treeRepository;
    private final PersonRepository personRepository;
    private final TreeRelationshipRepository relationshipRepository;

    public TreeService(TreeRepository treeRepository,
                       PersonRepository personRepository,
                       TreeRelationshipRepository relationshipRepository) {
        this.treeRepository = treeRepository;
        this.personRepository = personRepository;
        this.relationshipRepository = relationshipRepository;
    }

    public List<Tree> getAllTrees() {
        return treeRepository.findAllWithMembers();
    }

    public Optional<Tree> getTree(Long id) {
        return treeRepository.findById(id);
    }

    public List<Person> getPersonsForTree(Long treeId) {
        // Note: In the new schema, persons are not directly linked to trees via tree_id
        // Tree relationships are now managed through tree_relationship table
        return List.of();
    }

    public TreeData getTreeData(Long treeId) {
        Tree tree = treeRepository.findById(treeId).orElse(null);
        if (tree == null) {
            return new TreeData(List.of(), List.of());
        }

        // Get relationships for this tree
        List<TreeRelationship> relationships = relationshipRepository.findByTreeId(treeId);

        // Build members list from relationships
        Set<Long> personIds = new HashSet<>();
        for (TreeRelationship rel : relationships) {
            personIds.add(rel.personId());
        }

        List<SvgMember> members = new ArrayList<>();
        for (Long personId : personIds) {
            personRepository.findById(personId).ifPresent(p -> {
                members.add(new SvgMember(
                    String.valueOf(p.id()),
                    p.fullName(),
                    p.birthYear(),
                    p.deathYear()
                ));
            });
        }

        // Build parent-child relationships for SVG using ancestry IDs from tree_relationship
        List<SvgRelationship> svgRelationships = new ArrayList<>();
        for (TreeRelationship rel : relationships) {
            String childId = rel.ancestryId();
            if (childId == null) childId = String.valueOf(rel.personId());

            // Add parent relationships
            if (rel.parent1AncestryId() != null && !rel.parent1AncestryId().isBlank()) {
                svgRelationships.add(new SvgRelationship("parent-child", rel.parent1AncestryId(), childId));
            }
            if (rel.parent2AncestryId() != null && !rel.parent2AncestryId().isBlank()) {
                svgRelationships.add(new SvgRelationship("parent-child", rel.parent2AncestryId(), childId));
            }
        }

        return new TreeData(members, svgRelationships);
    }

    public record TreeData(List<SvgMember> members, List<SvgRelationship> relationships) {}

    public record SvgMember(String id, String name, Integer birthYear, Integer deathYear) {}

    public record SvgRelationship(String type, String parentId, String childId) {}
}

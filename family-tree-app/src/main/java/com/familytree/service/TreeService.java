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
        return personRepository.findByTreeId(treeId);
    }

    public TreeData getTreeData(Long treeId) {
        Tree tree = treeRepository.findById(treeId).orElse(null);
        if (tree == null) {
            return new TreeData(List.of(), List.of());
        }

        List<Person> persons = personRepository.findByTreeId(treeId);

        // Get relationships using ancestry_tree_id
        List<TreeRelationship> relationships = tree.ancestryTreeId() != null
            ? relationshipRepository.findByAncestryTreeId(tree.ancestryTreeId())
            : List.of();

        // Build members list for SVG
        List<SvgMember> members = new ArrayList<>();
        for (Person p : persons) {
            members.add(new SvgMember(
                p.ancestryPersonId() != null ? p.ancestryPersonId() : String.valueOf(p.id()),
                p.fullName(),
                p.birthYearEstimate(),
                p.deathYearEstimate()
            ));
        }

        // Build parent-child relationships for SVG
        List<SvgRelationship> svgRelationships = new ArrayList<>();
        for (TreeRelationship rel : relationships) {
            String childId = rel.ancestryPersonId();

            // Add father relationship
            if (rel.fatherId() != null && !rel.fatherId().isBlank()) {
                svgRelationships.add(new SvgRelationship("parent-child", rel.fatherId(), childId));
            }

            // Add mother relationship
            if (rel.motherId() != null && !rel.motherId().isBlank()) {
                svgRelationships.add(new SvgRelationship("parent-child", rel.motherId(), childId));
            }
        }

        return new TreeData(members, svgRelationships);
    }

    public record TreeData(List<SvgMember> members, List<SvgRelationship> relationships) {}

    public record SvgMember(String id, String name, Integer birthYear, Integer deathYear) {}

    public record SvgRelationship(String type, String parentId, String childId) {}
}

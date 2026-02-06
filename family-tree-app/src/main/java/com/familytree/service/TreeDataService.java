package com.familytree.service;

import com.familytree.model.Person;
import com.familytree.repository.PersonRepository;
import org.springframework.stereotype.Service;

import java.util.*;

@Service
public class TreeDataService {

    private final PersonRepository personRepository;

    public TreeDataService(PersonRepository personRepository) {
        this.personRepository = personRepository;
    }

    // ========== DESCENDANTS ==========

    public Optional<TreeNode> buildDescendantsHierarchy(Long personId, int maxDepth) {
        return personRepository.findById(personId)
                .map(person -> buildDescendantNode(person, new HashSet<>(), maxDepth));
    }

    private TreeNode buildDescendantNode(Person person, Set<Long> visited, int remainingDepth) {
        if (visited.contains(person.id()) || remainingDepth <= 0) {
            return null;
        }
        visited.add(person.id());

        TreeNode node = new TreeNode(
                person.id(),
                person.fullBirthName(),
                formatDates(person),
                detectGender(person),
                person.avatarPath()
        );

        // Spouse info
        List<Person> spouses = personRepository.findSpouses(person.id());
        if (!spouses.isEmpty()) {
            Person spouse = spouses.get(0);
            node.setSpouse(spouse.fullBirthName());
            node.setSpouseId(spouse.id());
        }

        // Children
        List<Person> children = personRepository.findChildren(person.id());
        if (!children.isEmpty()) {
            List<TreeNode> childNodes = new ArrayList<>();
            for (Person child : children) {
                TreeNode childNode = buildDescendantNode(child, visited, remainingDepth - 1);
                if (childNode != null) {
                    childNodes.add(childNode);
                }
            }
            if (!childNodes.isEmpty()) {
                // Sort by birth year
                childNodes.sort(Comparator.comparing(TreeNode::getDates));
                node.setChildren(childNodes);
            }
        }

        return node;
    }

    // ========== ANCESTORS ==========

    public Optional<TreeNode> buildAncestorsHierarchy(Long personId, int maxDepth) {
        return personRepository.findById(personId)
                .map(person -> buildAncestorNode(person, new HashSet<>(), maxDepth));
    }

    private TreeNode buildAncestorNode(Person person, Set<Long> visited, int remainingDepth) {
        if (visited.contains(person.id()) || remainingDepth <= 0) {
            return null;
        }
        visited.add(person.id());

        TreeNode node = new TreeNode(
                person.id(),
                person.fullBirthName(),
                formatDates(person),
                detectGender(person),
                person.avatarPath()
        );

        // Spouse info
        List<Person> spouses = personRepository.findSpouses(person.id());
        if (!spouses.isEmpty()) {
            Person spouse = spouses.get(0);
            node.setSpouse(spouse.fullBirthName());
            node.setSpouseId(spouse.id());
        }

        // Parents (stored as "children" for D3 tree layout - it just means "next level")
        List<TreeNode> parents = new ArrayList<>();

        if (person.fatherId() != null) {
            personRepository.findById(person.fatherId())
                    .map(father -> buildAncestorNode(father, visited, remainingDepth - 1))
                    .ifPresent(parents::add);
        }

        if (person.motherId() != null) {
            personRepository.findById(person.motherId())
                    .map(mother -> buildAncestorNode(mother, visited, remainingDepth - 1))
                    .ifPresent(parents::add);
        }

        if (!parents.isEmpty()) {
            node.setChildren(parents);
        }

        return node;
    }

    // ========== MRCA PATH ==========

    public Optional<TreeNode> buildMrcaPath(Long personAId, Long personBId) {
        // Step 1: Get ancestors of both with depth and discovery order tracking
        Map<Long, int[]> ancestorsA = getAncestorsWithDepthAndOrder(personAId);
        Map<Long, int[]> ancestorsB = getAncestorsWithDepthAndOrder(personBId);

        // Step 2: Find common ancestors
        Set<Long> common = new HashSet<>(ancestorsA.keySet());
        common.retainAll(ancestorsB.keySet());

        if (common.isEmpty()) {
            return Optional.empty();
        }

        // Step 3: MRCA = lowest combined depth, then lowest combined discovery order
        Long mrcaId = common.stream()
                .min(Comparator.comparingInt((Long id) -> ancestorsA.get(id)[0] + ancestorsB.get(id)[0])
                        .thenComparingInt(id -> ancestorsA.get(id)[1] + ancestorsB.get(id)[1]))
                .orElse(null);

        if (mrcaId == null) {
            return Optional.empty();
        }

        // Step 4: Build paths
        List<Long> pathA = buildPathToAncestor(personAId, mrcaId);
        List<Long> pathB = buildPathToAncestor(personBId, mrcaId);

        // Step 5: Construct tree with MRCA as root
        return personRepository.findById(mrcaId)
                .map(mrca -> buildMrcaTree(mrca, pathA, pathB));
    }

    private Map<Long, int[]> getAncestorsWithDepthAndOrder(Long personId) {
        Map<Long, int[]> ancestors = new HashMap<>();
        int[] order = {0};  // mutable counter
        collectAncestors(personId, 0, ancestors, order);
        return ancestors;
    }

    private void collectAncestors(Long personId, int depth, Map<Long, int[]> ancestors, int[] order) {
        if (personId == null || ancestors.containsKey(personId)) {
            return;
        }
        ancestors.put(personId, new int[]{depth, order[0]++});

        personRepository.findById(personId).ifPresent(person -> {
            collectAncestors(person.fatherId(), depth + 1, ancestors, order);
            collectAncestors(person.motherId(), depth + 1, ancestors, order);
        });
    }

    private List<Long> buildPathToAncestor(Long personId, Long ancestorId) {
        List<Long> path = new ArrayList<>();
        buildPathRecursive(personId, ancestorId, path);
        return path;
    }

    private boolean buildPathRecursive(Long currentId, Long targetId, List<Long> path) {
        if (currentId == null) {
            return false;
        }

        path.add(currentId);

        if (currentId.equals(targetId)) {
            return true;
        }

        Optional<Person> personOpt = personRepository.findById(currentId);
        if (personOpt.isEmpty()) {
            path.remove(path.size() - 1);
            return false;
        }

        Person person = personOpt.get();

        if (buildPathRecursive(person.fatherId(), targetId, path)) {
            return true;
        }
        if (buildPathRecursive(person.motherId(), targetId, path)) {
            return true;
        }

        path.remove(path.size() - 1);
        return false;
    }

    private TreeNode buildMrcaTree(Person mrca, List<Long> pathA, List<Long> pathB) {
        TreeNode root = new TreeNode(
                mrca.id(),
                mrca.fullName(),
                formatDates(mrca),
                detectGender(mrca),
                mrca.avatarPath()
        );

        List<TreeNode> branches = new ArrayList<>();

        // Path A: reverse to go from MRCA's child down to target person (skip MRCA at the end)
        if (pathA.size() > 1) {
            List<Long> reversedA = new ArrayList<>(pathA.subList(0, pathA.size() - 1));
            Collections.reverse(reversedA);
            TreeNode branchA = buildPathBranch(reversedA);
            if (branchA != null) {
                branches.add(branchA);
            }
        }

        // Path B: reverse to go from MRCA's child down to target person (skip MRCA at the end)
        if (pathB.size() > 1) {
            List<Long> reversedB = new ArrayList<>(pathB.subList(0, pathB.size() - 1));
            Collections.reverse(reversedB);
            TreeNode branchB = buildPathBranch(reversedB);
            if (branchB != null) {
                branches.add(branchB);
            }
        }

        if (!branches.isEmpty()) {
            root.setChildren(branches);
        }

        return root;
    }

    private TreeNode buildPathBranch(List<Long> path) {
        if (path.isEmpty()) {
            return null;
        }

        // Build from end to start (ancestor to descendant)
        TreeNode current = null;
        for (int i = path.size() - 1; i >= 0; i--) {
            Long personId = path.get(i);
            Person person = personRepository.findById(personId).orElse(null);
            if (person == null) continue;

            TreeNode node = new TreeNode(
                    person.id(),
                    person.fullBirthName(),
                    formatDates(person),
                    detectGender(person),
                    person.avatarPath()
            );

            if (current != null) {
                node.setChildren(List.of(current));
            }
            current = node;
        }

        return current;
    }

    // ========== HELPERS ==========

    private String formatDates(Person person) {
        StringBuilder dates = new StringBuilder();
        if (person.birthYear() != null) {
            dates.append(person.birthYear());
        }
        dates.append("-");
        if (person.deathYear() != null) {
            dates.append(person.deathYear());
        }
        return dates.toString();
    }

    private String detectGender(Person person) {
        if (person.gender() != null && !person.gender().isBlank()) {
            return person.gender();
        }
        return "U";
    }

    // ========== DTO ==========

    public static class TreeNode {
        private final Long id;
        private final String name;
        private final String dates;
        private final String gender;
        private final String avatarPath;
        private String spouse;
        private Long spouseId;
        private List<TreeNode> children;

        public TreeNode(Long id, String name, String dates, String gender, String avatarPath) {
            this.id = id;
            this.name = name;
            this.dates = dates;
            this.gender = gender;
            this.avatarPath = avatarPath;
        }

        // Getters
        public Long getId() { return id; }
        public String getName() { return name; }
        public String getDates() { return dates; }
        public String getGender() { return gender; }
        public String getAvatarPath() { return avatarPath; }
        public String getSpouse() { return spouse; }
        public Long getSpouseId() { return spouseId; }
        public List<TreeNode> getChildren() { return children; }

        // Setters
        public void setSpouse(String spouse) { this.spouse = spouse; }
        public void setSpouseId(Long spouseId) { this.spouseId = spouseId; }
        public void setChildren(List<TreeNode> children) { this.children = children; }
    }
}
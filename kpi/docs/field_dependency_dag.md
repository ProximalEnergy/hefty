# Field Dependency DAG

This graph shows dependencies across registry fields (`input -> output`).
Zoom and pan to explore; click a node to reveal its label.
Colors: gray = transform/intermediate, orange = download fields, green = final
KPIs.

<div id="field-dag-selection" style="margin-top: 0.75rem;">
  Selected field:
  <code id="field-dag-selected-name">none</code>
  <a
    id="field-dag-open-docs"
    href="#"
    target="_self"
    rel="noopener"
    style="
      margin-left: 0.75rem;
      display: none;
      font-weight: 600;
      text-decoration: underline;
    "
    >Open docs</a
  >
</div>
<div id="field-dependency-dag-canvas" style="height: 75vh; width: 100%;"></div>

<script src="https://unpkg.com/cytoscape@3.30.0/dist/cytoscape.min.js"></script>
<script>
  window.addEventListener("load", () => {
    const graphData = window.FIELD_DEP_GRAPH;
    const container = document.getElementById("field-dependency-dag-canvas");
    const selectedName = document.getElementById("field-dag-selected-name");
    const openDocsLink = document.getElementById("field-dag-open-docs");

    if (!graphData || !container || !selectedName || !openDocsLink) {
      if (container) {
        container.innerText = "Unable to load field dependency graph.";
      }
      return;
    }

    const cy = cytoscape({
      container,
      elements: [...graphData.nodes, ...graphData.edges],
      layout: {
        name: "cose",
        animate: false,
        fit: true,
        padding: 30,
        nodeRepulsion: 70000,
        idealEdgeLength: 40,
        edgeElasticity: 60,
      },
      style: [
        {
          selector: "node",
          style: {
            label: "",
            "background-color": "#455a64",
            width: 12,
            height: 12,
            opacity: 0.95,
            "border-width": 1,
            "border-color": "#263238",
          },
        },
        {
          selector: 'node[phase = "download"]',
          style: {
            "background-color": "#ef6c00",
            "border-color": "#e65100",
          },
        },
        {
          selector: 'node[phase = "kpi"]',
          style: {
            "background-color": "#2e7d32",
            "border-color": "#1b5e20",
          },
        },
        {
          selector: "node[hub = 1]",
          style: {
            width: 20,
            height: 20,
            "border-width": 2,
          },
        },
        {
          selector: "node:selected",
          style: {
            label: "data(label)",
            "font-size": "12px",
            color: "#ffffff",
            "text-background-opacity": 0.85,
            "text-background-color": "#263238",
            "text-background-padding": "2px",
            "text-background-shape": "roundrectangle",
            "text-valign": "top",
            "text-margin-y": "-8px",
            width: 22,
            height: 22,
            "border-width": 3,
            "border-color": "#1f2933",
          },
        },
        {
          selector: "edge",
          style: {
            width: 1.4,
            opacity: 0.35,
            "line-color": "#78909c",
            "target-arrow-color": "#78909c",
            "target-arrow-shape": "triangle",
            "curve-style": "bezier",
          },
        },
        {
          selector: ".zoomed-out",
          style: {
            width: 18,
            height: 18,
          },
        },
      ],
      minZoom: 0.08,
      maxZoom: 2.5,
      wheelSensitivity: 0.18,
    });

    const degreeById = new Map();
    for (const edge of graphData.edges) {
      const source = edge.data.source;
      const target = edge.data.target;
      degreeById.set(source, (degreeById.get(source) || 0) + 1);
      degreeById.set(target, (degreeById.get(target) || 0) + 1);
    }

    cy.nodes().forEach((node) => {
      const degree = degreeById.get(node.id()) || 0;
      if (degree >= 20) {
        node.data("hub", 1);
      }
    });

    const docsBasePath =
      typeof __md_scope !== "undefined"
        ? __md_scope.pathname.replace(/\/$/, "")
        : "";

    const resetSelectionUi = () => {
      selectedName.textContent = "none";
      openDocsLink.style.display = "none";
      openDocsLink.href = "#";
    };

    const updateSelectionUi = (node) => {
      selectedName.textContent = node.id();
      const canLink = Boolean(node.data("canLinkToDocs"));
      const docPath = node.data("docPath");
      const docAnchor = node.data("docAnchor");
      if (canLink && docPath && docAnchor) {
        openDocsLink.href = `${docsBasePath}${docPath}#${docAnchor}`;
        openDocsLink.style.display = "inline";
      } else {
        openDocsLink.style.display = "none";
        openDocsLink.href = "#";
      }
    };

    const applyZoomStyling = () => {
      if (cy.zoom() < 0.25) {
        cy.nodes().addClass("zoomed-out");
      } else {
        cy.nodes().removeClass("zoomed-out");
      }
    };

    const focusNode = (node) => {
      cy.nodes().unselect();
      node.select();
      updateSelectionUi(node);
      const neighborhood = node.closedNeighborhood();
      cy.animate({
        fit: {
          eles: neighborhood,
          padding: 120,
        },
        duration: 300,
      });
    };

    cy.on("select", "node", (event) => {
      updateSelectionUi(event.target);
    });
    cy.on("tap", "node", (event) => {
      updateSelectionUi(event.target);
    });
    cy.on("unselect", "node", () => {
      const selected = cy.$("node:selected");
      if (selected.length === 0) {
        resetSelectionUi();
      }
    });

    const focusField = new URLSearchParams(window.location.search).get("focus");
    if (focusField) {
      const focusNodeMatch = cy.getElementById(focusField);
      if (focusNodeMatch.length > 0) {
        focusNode(focusNodeMatch);
      } else {
        resetSelectionUi();
      }
    } else {
      resetSelectionUi();
    }

    cy.on("zoom", applyZoomStyling);
    applyZoomStyling();
  });
</script>

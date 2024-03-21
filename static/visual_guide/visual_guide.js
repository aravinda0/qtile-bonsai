;(function () {
  function annotateExamples() {
    const examples = document.getElementsByClassName("example");
    for (example of examples) {
      const lhs = example.getElementsByClassName("lhs");
      const rhs = example.getElementsByClassName("rhs");

      const line = new LeaderLine({
        start: lhs[0],
        end: rhs[0],
        size: 1,
        endPlugSize: 3,
        color: "#000",
        path: "grid",
        middleLabel: LeaderLine.pathLabel(
          example.dataset.command,
          { fontFamily: "monospace", fontSize: "0.8rem", color: "#000" }
        ),
      });
    }
   }

  document.addEventListener("DOMContentLoaded", () => {
    annotateExamples();
  });
})()

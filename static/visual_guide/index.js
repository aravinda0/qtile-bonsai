;(function () {

  /**
   * These match with the media queries specified in `index.css`. Manually kept in sync
   * for now.
   */
  const mediaQueries = [
    { 
      q: window.matchMedia("(max-width: 480px )"), 
      fraction: 0.35,
      arrowConfig: {
        endPlugSize: 2,
        endSocketGravity: undefined,
      }
    },
    { 
      q: window.matchMedia("(max-width: 768px )"), 
      fraction: 0.45,
      arrowConfig: {
        endPlugSize: 2,
        endSocketGravity: undefined,
      }
    },
    { 
      q: window.matchMedia("(max-width: 1024px )"), 
      fraction: 0.70,
      arrowConfig: {
        endPlugSize: 3,
        endSocketGravity: [-100, 0],
      }
    },
  ];

  function pxToRem(px) {
    return px / parseFloat(getComputedStyle(document.documentElement).fontSize);
  }

  function remifyAndShrink(fraction) {
    const hardDimensionClasses = ["tree", "node-p", "tc-bar"];
    for (const cls of hardDimensionClasses) {
      for (const elem of document.getElementsByClassName(cls)) {
        const remW = pxToRem(parseFloat(elem.style.width));
        elem.style.width = `${fraction * remW}rem`;

        const remH = pxToRem(parseFloat(elem.style.height));
        elem.style.height = `${fraction * remH}rem`;
      }
    }
  }

  /**
   * Resize our examples via JS. 
   * We can't use CSS media queries for this since the elements are generated with
   * inline'd widths/heights from the jinja/python backend.
   */
  function performPoorMansMediaQueries() {
    for (const mq of mediaQueries) {
      if (mq.q.matches) {
        remifyAndShrink(mq.fraction);
        break;
      }
    }
  }

  function annotateExamples() {
    const examples = document.getElementsByClassName("example");

    for (const example of examples) {
      const lhs = example.getElementsByClassName("lhs");
      const rhsItems = example.getElementsByClassName("rhs");

      let arrowConfig = {
        endSocketGravity: [-400, 0],
        endPlugSize: 3,
      };
      for (const mq of mediaQueries) {
        if (mq.q.matches) {
          console.log(mq);
          arrowConfig = { ...mq.arrowConfig };
          break;
        }
      }

      for (const rhs of rhsItems) {
        const line = new LeaderLine({
          start: lhs[0],
          end: rhs,
          size: 1,
          color: "#000",
          path: "grid",
          ...arrowConfig,
        });
      }
    }
  }

  document.addEventListener("DOMContentLoaded", () => {
    performPoorMansMediaQueries();
    annotateExamples();
  });

})()


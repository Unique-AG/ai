document.addEventListener("DOMContentLoaded", () => {
  // Simple approach: look for any element with data-open-source attribute or containing "open-source" text
  setTimeout(() => {
    for (const d of document.querySelectorAll("details")) {
      const s = d.querySelector("summary");
      if (!s) continue;
      const txt = s.textContent || "";
      
      // Only work with source code sections
      if (/source code/i.test(txt)) {
        // Check if the page contains an "open-source" comment anywhere near this section
        const pageHTML = document.documentElement.innerHTML;
        const detailsHTML = d.outerHTML;
        const detailsIndex = pageHTML.indexOf(detailsHTML);
        
        // Look for "open-source" comment in the 1000 characters before this details block
        const beforeHTML = pageHTML.substring(Math.max(0, detailsIndex - 1000), detailsIndex);
        if (beforeHTML.includes("open-source")) {
          d.setAttribute("open", "");
          console.log("Opening source code section due to open-source marker");
        }
      }
    }
  }, 100); // Small delay to ensure DOM is fully loaded
});


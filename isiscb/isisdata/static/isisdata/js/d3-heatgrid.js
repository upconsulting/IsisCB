// this script uses D3.js to generate a heatgrid type chart 
// (e.g.: https://observablehq.com/@d3/the-impact-of-vaccines)

const data = JSON.parse(
  document.currentScript.nextElementSibling.textContent
);

// Declare the chart dimensions and margins.
const marginTop = 20;
const marginRight = 11;
const marginBottom = 40;
const marginLeft = 160;
const rowHeight = 12;
const width = 1000;
const height = rowHeight * data.names.length + marginTop + marginBottom;

// Create the SVG container.
const svg = d3.select("#theses-by-school-chart-container").append("svg")
    .attr("viewBox", [0, 0, width, height])
    .attr("viewBox", [0, 0, width, height])
    .attr("width", width)
    .attr("height", height)
    .attr("style", "max-width: 100%; height: auto;");

// Create the scales.
const x = d3.scaleLinear()
    .domain([d3.min(data.years), d3.max(data.years) + 1])
    .rangeRound([marginLeft, width - marginRight])

const y = d3.scaleBand()
    .domain(data.names)
    .rangeRound([marginTop, height - marginBottom])

const color = d3.scaleSequentialSqrt([0, d3.max(data.values, d => d3.max(d))], d3.interpolatePuRd);

// Append the axes.
svg.append("g")
    .call(g => g.append("g")
        .attr("transform", `translate(0,${marginTop})`)
        .call(d3.axisTop(x).ticks(null, "d"))
        .call(g => g.select(".domain").remove()))

svg.append("g")
    .attr("transform", `translate(${marginLeft},0)`)
    .call(d3.axisLeft(y).tickSize(0))
    .call(g => g.select(".domain").remove());

svg.append("g")
    .selectAll("g")
    .data(data.values)
    .join("g")
    .attr("transform", (d, i) => `translate(0,${y(data.names[i])})`)
    .selectAll("rect")
    .data(d => d)
    .join("rect")
    .attr("x", (d, i) => x(data.years[i]) + 1)
    .attr("width", (d, i) => x(data.years[i] + 1) - x(data.years[i]) - 1)
    .attr("height", y.bandwidth() - 1)
    .attr("fill", d => isNaN(d) ? "#eee" : d === 0 ? "#fff" : color(d))
    .append("title")
    .text((d, i) => `${d} theses in ${data.years[i]}`);
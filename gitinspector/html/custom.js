function resize_main_div() {
    const s = $("#summary_div").width();
    const w = $("#introduction_div").width() - s - 80;
    const h = $("#introduction_div").height();
    d3.selectAll("#main_div").style("width", w);
    d3.selectAll("#main_div").style("left", s + 30);
    d3.selectAll("#main_div").style("top", h - 20);
    d3.selectAll("#summary_div").style("top", h - 20);
}

function generate_pie(group, radius, data, value_fun, color_fun) {
    // Generator for the pie
    var pie_maker = d3.pie().value(value_fun);

    // Generator for the arcs
    var arc_maker = d3.arc().innerRadius(radius/2.5).outerRadius(radius);

    // Generate groups
    var arcs = group.selectAll("arc")
        .data(pie_maker(data))
        .enter()
        .append("g")
        .attr("class", "arc");

    // Draw arc paths
    arcs.append("path")
        .attr("id", function(d, i) { return "path_" + i; })
        .attr("fill", color_fun)
        .attr("stroke", "white")
        .attr("d", arc_maker);

    return arcs;
}

function recolor_table_rows(id) {
    var cpt = 0;
    d3.selectAll("table#" + id + " tbody tr").each(function() {
        var elem = d3.select(this);
        if (this.style["display"] == "") {
            this.className = (cpt % 2 == 0) ? "even" : "odd";
            cpt++;
        }
    });
}

function generate_sortable_table(id, titles, data, filter) {
    var thead = d3.select("table#" + id + " thead"),
        tbody = d3.select("table#" + id + " tbody");

    // Create lines of table
    var lines = tbody.selectAll()
        .data(data)
        .enter()
        .append("tr")
        .attr("id", function (d,i) { return "line_" + i; });

    // Fill the lines with data
    titles.forEach(function (t) {
        lines.append("td").html(function(d) { return d[t]; });
    });
    lines.append("td").filter(filter)
        .append("svg")
        .attr("width", 30).attr("height", 30)
        .append("rect")
        .attr("x", 5).attr("y", 5)
        .attr("width", 20).attr("height", 20)
        .attr("fill", function(d,i) { return d.color; });

    // Hide authors with minimal involvement
    var filtered_lines = lines.filter(function (d) { return !filter(d); });

    // Display these same authors when clicking on footer
    if (filtered_lines.size() > 1) {
        filtered_lines.style("display", "none");
        var th = d3.select("table#" + id + " tfoot tr th");
        var th_txt = "Display minor authors (" + filtered_lines.size() + ")";
        th.text(th_txt);
        th.on("click", function(d) {
            if (this.className == "visible") {
                filtered_lines.style("display", "none");
                recolor_table_rows(id);
                d3.select(this).text(th_txt);
                this.className = "";
            } else {
                filtered_lines.style("display", "");
                recolor_table_rows(id);
                d3.select(this).text("Hide minor authors");
                this.className = "visible";
            }
        });
    }
    recolor_table_rows(id);

    // Make the columns sortable
    d3.selectAll("table#" + id + " tr th").data(titles).on("click", function(d) {
        if (this.className == "asc") {
            lines.sort(function(a, b) { return b[d] > a[d]; });
            recolor_table_rows(id);
            this.className = "desc";
        } else {
            lines.sort(function(a, b) { return b[d] < a[d]; });
            recolor_table_rows(id);
            this.className = "asc";
        }
    });

    return lines;
}

function link_table_and_pie(lines, arcs) {
    var length = arcs.size();
    arcs.on("mouseover", function(d, i){
        if (i+1 != length) {
            d3.select(this).select("path").attr("fill", d3.color(d.data.color).brighter());
            lines.filter(function () { return this.id == ("line_" + i)}).classed("hovered", true);
        }
    });
    arcs.on("mouseout", function(d, i){
        if (i+1 != length) {
            d3.select(this).select("path").attr("fill", d.data.color);
            lines.filter(function () { return this.id == ("line_" + i)}).classed("hovered", false);
        }
    });

    // Link lines with pie chart sections
    lines.on("mouseover", function(d, i){
        d3.select(this).classed("hovered", true);
        if (i+1 != length) {
            arcs.select("#path_" + i).attr("fill", d3.color(d.color).brighter());
        }
    });
    lines.on("mouseout", function(d, i){
        d3.select(this).classed("hovered", false);
        if (i+1 != length) {
            arcs.select("#path_" + i).attr("fill", d.color);
        }
    });
}

function generate_table(div, id, data) {
    var tbody = div.append("table").attr("id", id)
        .classed("git2", "true").append("tbody");

    var lines = tbody.selectAll()
        .data(data).enter()
        .append("tr")
        .attr("id", function (d,i) { return "line_" + i; });
    Object.keys(data[0]).forEach(function(t) {
        var td = lines.append("td")
            .html(function(d) { return d[t];})
            .each(function(d) { if (t == "severity")
                d3.select(this).classed(d[t],true);
                               });
    });
    recolor_table_rows(id);
}

function register_box(label, div) {
    d3.selectAll("ul#summary_ul").append("li").append("a").attr("href", "#").html(label)
        .on("click", function () {
            const top = $("#" + div).offset().top - 110;
            console.log(top);
            $('html,body').animate({scrollTop: top}, 100);
        });
}

$(document).ready(function() {
    // Adjust the size of the main div
    resize_main_div();
    $( window ).resize(resize_main_div);
});

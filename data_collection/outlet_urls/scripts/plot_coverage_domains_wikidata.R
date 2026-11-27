# Share of DNR outlets (2016-2026) per country with a candidate domain after the Wikidata lookup.
# Input:  outlet_urls/wikidata_candidates.csv (wikidata_prefill.py), data_collection/countries.csv
# Output: outlet_urls/figures/coverage_domains_wikidata.png
# Run from data_collection/outlet_urls:  Rscript scripts/plot_coverage_domains_wikidata.R
library(dplyr); library(ggplot2); library(readr)

lev <- c("Wikidata website, close name match in the country", "Wikidata website, weaker match",
         "Domain printed in the DNR only", "No domain yet")
d <- read_csv("wikidata_candidates.csv", show_col_types = FALSE, na = "") |>
  mutate(status = case_when(
    !is.na(wd_domain) & label_sim >= 0.9 & country_match == "yes" ~ lev[1],
    !is.na(wd_domain) ~ lev[2],
    !is.na(printed_domain) ~ lev[3],
    TRUE ~ lev[4])) |>
  count(country, status) |>
  group_by(country) |>
  mutate(total = sum(n), share = n / total, covered = 1 - sum(share[status == lev[4]])) |>
  ungroup() |>
  left_join(read_csv("../countries.csv", show_col_types = FALSE) |> select(country_name = country, iso3), by = c("country" = "iso3")) |>
  mutate(label = paste0(country_name, " (", total, ")"), status = factor(status, levels = rev(lev)))
ord <- d |> filter(status == lev[1]) |> arrange(share) |> pull(label)
d <- d |> mutate(label = factor(label, levels = union(ord, unique(label))))

p <- ggplot(d, aes(share, label, fill = status)) +
  geom_col(width = 0.72, colour = "white", linewidth = 0.6) +
  geom_text(data = distinct(d, label, covered), aes(x = 1.01, y = label, label = scales::percent(covered, accuracy = 1)),
            inherit.aes = FALSE, hjust = 0, size = 3.1, colour = "#666666") +
  scale_fill_manual(values = setNames(c("#257de0", "#00b894", "#f47230", "#d9d9d9"), lev), breaks = lev) +
  scale_x_continuous(labels = scales::percent, breaks = seq(0, 1, 0.25), limits = c(0, 1.07), expand = c(0, 0)) +
  guides(fill = guide_legend(nrow = 2)) +
  labs(title = "Candidate domains per country after the Wikidata lookup",
       subtitle = "Share of DNR outlets 2016-2026 (number of outlets in brackets); right: share with any candidate domain",
       x = NULL, y = NULL, fill = NULL) +
  theme_minimal(base_size = 11) +
  theme(panel.grid.major.y = element_blank(), panel.grid.minor = element_blank(), legend.position = "bottom",
        legend.justification = "left", plot.title.position = "plot", plot.title = element_text(face = "bold"),
        plot.subtitle = element_text(colour = "#666666", size = 9), axis.text.y = element_text(colour = "#191919"),
        plot.background = element_rect(fill = "white", colour = NA))
ggsave("figures/coverage_domains_wikidata.png", p, width = 8, height = 8.2, dpi = 200)

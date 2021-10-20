from plotnine import element_blank, element_text, theme

background_effectsize = theme(
    panel_background=element_blank(),
    panel_grid_major_y=element_blank(),
    axis_text_x=element_text(color="black", angle=90, hjust=1, size=12),
    axis_text_y=element_text(color="black", size=12),
    legend_text=element_text(color="black", size=16),
    legend_title=element_text(color="black", size=16),
    axis_title=element_text(size=16, face="bold"),
    strip_text_x=element_text(size=12),
    legend_background=element_blank(),
    legend_key=element_blank(),
    panel_grid_major=element_blank(),
    panel_grid_minor=element_blank(),
)

standard_background = theme(
    panel_background=element_blank(),
    panel_grid_major_y=element_blank(),
    axis_text_x=element_text(color="black", size=12),
    axis_text_y=element_text(color="black", size=12),
    legend_text=element_text(color="black", size=10),
    legend_title=element_text(color="black", size=12),
    axis_title=element_text(size=12),
    strip_text_x=element_text(size=12),
    legend_background=element_blank(),
    legend_key=element_blank(),
    panel_grid_major=element_blank(),
    panel_grid_minor=element_blank(),
    axis_ticks=element_blank(),
)

standard_background_rotatex_nojust = theme(
    panel_background=element_blank(),
    panel_grid_major_y=element_blank(),
    axis_text_x=element_text(color="black", angle=90, size=12),
    axis_text_y=element_text(color="black", size=12),
    legend_text=element_text(color="black", size=10),
    legend_title=element_text(color="black", size=12),
    axis_title=element_text(size=12),
    strip_text_x=element_text(size=12),
    legend_background=element_blank(),
    legend_key=element_blank(),
    panel_grid_major=element_blank(),
    panel_grid_minor=element_blank(),
    axis_ticks=element_blank(),
)

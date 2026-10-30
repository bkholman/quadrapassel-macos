blueprints = custom_target('blueprints',
    input: files(
        'adaptive-card.blp',
        'more-info-button.blp',
        'rules-dialog.blp',
        'shortcuts-dialog.blp'
    ),
    output: [
        'adaptive-card.ui',
        'more-info-button.ui',
        'rules-dialog.ui',
        'shortcuts-dialog.ui',
    ],
    command: [find_program('blueprint-compiler'), 'batch-compile', meson.current_build_dir(), '@CURRENT_SOURCE_DIR@', '@INPUT@'],
)

quadrapassel_sources = [
    'vapi/config.vapi',
    'runtime-paths.vala',
    'adaptive-card.vala',
    'game-view.vala',
    'game.vala',
    'more-info-button.vala',
    'preview.vala',
    'quadrapassel.vala'
]

platform_dependencies = []
platform_vala_args = []
platform_link_args = []
if have_gamepad
    quadrapassel_sources += 'vapi/input-event-codes.vapi'
    platform_dependencies += manette_dependency
    platform_vala_args += '--define=ENABLE_GAMEPAD'
endif
if is_macos
    quadrapassel_sources += ['macos-support.c', 'vapi/macos-support.vapi']
    platform_vala_args += '--define=MACOS'
    # Leave room for the packager to rewrite library install names.
    platform_link_args += '-Wl,-headerpad_max_install_names'
endif

resources_conf = configuration_data()
resources_conf.set('app-id', app_id)
resources_conf.set('base-id-slashed', '/' + base_id.replace('.', '/'))
resources = gnome.compile_resources(
    'resources',
    configure_file(
        input: '@0@.gresource.xml'.format(base_id),
        output: '@BASENAME@',
        configuration: resources_conf,
    ),
    source_dir: 'gresource',
    c_name: 'quadrapassel',
    dependencies: blueprints
)
quadrapassel_sources += resources
executable(meson.project_name(),
    quadrapassel_sources,
    install: true,
    c_args: [
        '-include', 'config.h'
    ],
    vala_args: platform_vala_args + [
        '--target-glib', '2.44',
        '--vapidir', join_paths(meson.current_source_dir(), 'vapi')
    ],
    link_args: platform_link_args,
    dependencies: platform_dependencies + [
        gtk_dependency,
        libadwaita_dependency,
        libgnome_games_support_dependency,
        libm_dependency
    ]
)

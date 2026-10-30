project('quadrapassel', 'vala', 'c',
        version: '51.0',
        meson_version: '>= 1.1')

# App ID
if get_option('profile') == 'development'
  profile = '.Devel'
else
  profile = ''
endif

base_id = 'org.gnome.Quadrapassel'
app_id = 'org.gnome.Quadrapassel@0@'.format(profile)

# used to install help
gnome = import('gnome')
# used for internationalization
i18n = import('i18n')

cc = meson.get_compiler('c')
is_macos = host_machine.system() == 'darwin'
if is_macos
  add_languages('objc', native: false)
endif

gtk_dependency = dependency('gtk4', version: '>= 4.4')
libadwaita_dependency = dependency('libadwaita-1', version: '>= 1.8')
libgnome_games_support = subproject ('libgnome-games-support',
	    		             default_options: [ 'superproject_name=quadrapassel', 'sounds=true' ])
libgnome_games_support_dependency = libgnome_games_support.get_variable ('lggs_dependency')
gamepad_option = get_option('gamepad')
if host_machine.system() == 'linux'
  # Preserve the existing Linux default; -Dgamepad=disabled allows keyboard-only builds.
  manette_dependency = dependency('manette-0.2', version: '>= 0.2.10',
                                  required: not gamepad_option.disabled())
  have_gamepad = not gamepad_option.disabled()
else
  if gamepad_option.enabled()
    error('Gamepad support currently requires Linux. Use -Dgamepad=disabled.')
  endif
  have_gamepad = false
endif
libm_dependency = cc.find_library('m', required : true)

localedir = join_paths(get_option('prefix'), get_option('localedir'))
datadir = join_paths(get_option('prefix'), get_option('datadir'))
soundsdir = join_paths(datadir, 'sounds', meson.project_name())
bindir = join_paths (get_option ('prefix'), get_option ('bindir'))

conf = configuration_data ()
conf.set_quoted ('APP_ID', app_id)
conf.set_quoted ('VERSION', meson.project_version())
conf.set_quoted ('GETTEXT_PACKAGE', meson.project_name())
conf.set_quoted ('SOUND_DIRECTORY', soundsdir)
conf.set_quoted ('LOCALEDIR', localedir)

configure_file(output: 'config.h', configuration: conf)
config_h_dir = include_directories('.')

python = import('python').find_installation()
language_data = custom_target('language-data',
  input: ['data/languages.json', 'po/LINGUAS'],
  output: 'language-data.vala',
  command: [python, files('build-aux/generate-languages.py'), '@INPUT0@', '@INPUT1@', '@OUTPUT@'],
)

subdir('data')
subdir('po')
subdir('src')

scoring_tests = executable('test-scoring',
    ['tests/test-scoring.vala', 'src/game.vala'],
    dependencies: [dependency('glib-2.0'), dependency('gobject-2.0'), libm_dependency],
)
test('game-scoring', scoring_tests)

scoreboard_tests = executable('test-scoreboard',
    'tests/test-scoreboard.vala',
    dependencies: [gtk_dependency, libadwaita_dependency, libgnome_games_support_dependency],
)
test('scoreboard-reset', scoreboard_tests)

localization_tests = executable('test-localization',
    ['tests/test-localization.vala', 'src/localization.vala', 'src/vapi/config.vapi', language_data],
    c_args: ['-include', 'config.h'],
    include_directories: config_h_dir,
    dependencies: [dependency('gio-2.0')],
)
test('language-selection', localization_tests)

if is_macos
    executable('test-localization-runtime',
        ['tests/localization-runtime.vala', 'src/localization.vala', 'src/runtime-paths.vala',
         'src/macos-support.c', 'src/macos-localization.m', 'src/vapi/config.vapi',
         'src/vapi/macos-support.vapi', language_data],
        c_args: ['-include', 'config.h'],
        vala_args: ['--define=MACOS'],
        link_args: ['-Wl,-headerpad_max_install_names'],
        include_directories: [config_h_dir, include_directories('src')],
        dependencies: [gtk_dependency, libadwaita_dependency,
                       dependency('appleframeworks', modules: ['Foundation'])],
    )
endif

gnome.post_install(
  gtk_update_icon_cache: true,
  glib_compile_schemas: true,
  update_desktop_database: not is_macos,
)

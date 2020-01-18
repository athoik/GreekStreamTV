from distutils.core import setup
import setup_translate

pkg = 'Extensions.GreekStreamTV'
setup (name = 'enigma2-plugin-extensions-greekstreamtv',
       version = '3.5',
       description = 'Watch live stream TV from Greece',
       package_dir = {pkg: 'plugin'},
       packages = [pkg],
       package_data = {pkg: ['icons/*.png', 'plugin.png', 'stream.xml', 'create.sh', 'update.sh', 'xml/*.xml']},
       cmdclass = setup_translate.cmdclass,
)

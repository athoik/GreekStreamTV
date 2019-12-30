from distutils.core import setup
import setup_translate

pkg = 'Extensions.GreekStreamTV'
setup (name = 'enigma2-plugin-extensions-greekstreamtv',
       version = '3.4',
       description = 'Watch live stream TV from Greece',
       package_dir = {pkg: 'plugin'},
       packages = [pkg],
       package_data = {pkg: ['channel_background.png', 'depends.sh', 'icons/*.png',
                             'plugin.png', 'stream.xml', 'update.sh', 'xml/*.xml']},
       cmdclass = setup_translate.cmdclass,
)

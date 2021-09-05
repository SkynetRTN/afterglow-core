const path = require("path");
const name = "Vue Typescript Admin";

module.exports = {
  publicPath: process.env.NODE_ENV === 'production'
    ? '/core/'
    : '/',
  lintOnSave: process.env.NODE_ENV === "development",
  pwa: {
    name: name,
  },
  transpileDependencies: ["vuex-module-decorators"],
  pluginOptions: {
    "style-resources-loader": {
      preProcessor: "scss",
      patterns: [
        // path.resolve(__dirname, 'src/styles/_variables.scss'),
        // path.resolve(__dirname, 'src/styles/_mixins.scss')
      ],
    },
  },
  chainWebpack(config) {
    // Provide the app's title in webpack's name field, so that
    // it can be accessed in index.html to inject the correct title.
    config.set("name", name);
  },
  devServer: {
    proxy: {
      "/core/*": {
        target: "http://127.0.0.1:5000",
        changeOrigin: true,
        secure: false,
        logLevel: "debug",
      },
    },
  },
};

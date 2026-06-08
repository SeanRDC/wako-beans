import next from "eslint-config-next";

const config = [...next, { ignores: [".next/**", "assets/**", "public/**"] }];

export default config;

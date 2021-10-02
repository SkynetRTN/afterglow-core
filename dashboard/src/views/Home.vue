<template>
  <div>
    <title-bar :title-stack="titleStack" />
    <section class="section is-main-section">
      
      <div class="columns is-desktop">
        <div class="column">
          <card-component
            title="Recent Jobs"
            icon="finance"
            header-icon="reload"
          >
            
          </card-component>
        </div>
      </div>
    </section>
  </div>
</template>

<script lang="ts">
import { Vue, Component } from "vue-property-decorator";

import { UserModule } from "../store/modules/user";

import TitleBar from "../components/TitleBar.vue";
import CardComponent from "../components/CardComponent.vue";

@Component({
  name: "home",

  components: {
    CardComponent,
    TitleBar
  }
})
export default class Home extends Vue {
  get titleStack() {
    return ["Dashboard"];
  }

  mounted() {
  }

}
</script>

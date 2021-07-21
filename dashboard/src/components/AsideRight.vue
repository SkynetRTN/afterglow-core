<template>
  <aside class="aside is-placed-right">
    <div ref="container" class="aside-container" @mouseenter="psUpdate">
      <aside-updates @data-updated="psInit" />
    </div>
  </aside>
</template>

<script lang="ts">
import { Vue, Component } from "vue-property-decorator";
import { mapState } from "vuex";
import PerfectScrollbar from "perfect-scrollbar";
import AsideUpdates from "./AsideUpdates.vue";
import { AppModule } from "../store/modules/app";

@Component({
  name: "AsideRight",
  components: { AsideUpdates },
})
export default class AsideRight extends Vue {
  private ps: PerfectScrollbar;
  get isAsideRightVisible() {
    return AppModule.isAsideRightVisible;
  }

  psInit() {
    this.ps = new PerfectScrollbar(this.$refs.container as Element);
  }

  psUpdate() {
    if (this.ps) {
      this.ps.update();
    }
  }
}
</script>

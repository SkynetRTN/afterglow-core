<template>
  <footer v-show="isFooterBarVisible" class="footer">
    <div class="container-fluid">
      <div class="level">
        <div class="level-left">
          <div class="level-item"></div>
        </div>
        <div class="level-right">
          <div class="level-item">
            <div class="logo">
              
            </div>
          </div>
        </div>
      </div>
    </div>
  </footer>
</template>

<script lang="ts">
import { Vue, Component } from "vue-property-decorator";
import dayjs from "dayjs";
import { mapState } from "vuex";
import { AppModule } from "../store/modules/app";

@Component({
  name: "FooterBar",
})
export default class FooterBar extends Vue {
  get year() {
    return dayjs().year();
  }

  get isFooterBarVisible() {
    return AppModule.isFooterBarVisible;
  }
}
</script>

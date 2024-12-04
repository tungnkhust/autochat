from autochat.group_chats import BaseGroupChat


class HandoffGroupChat(BaseGroupChat):
    def compile(self):
        super().compile()

        # setup handoff in inner group
        for participant in self.participants:
            # master handoff to participant
            self.master.add_handoff_tool(participant.to_handoff_tool())

            # participant handoff to master
            participant.add_handoff_tool(self.master.to_handoff_tool())

        # setup handoff with sub group
        for group in self.sub_groups:
            # master of group handoff to sub group
            self.master.add_handoff_tool(group.to_handoff_tool())
            # sub group handoff to outer group
            group.add_outer_handoff_tool(self.to_handoff_tool())

        # setup handoff with supper group
        for group in self.supper_groups:
            # master handoff to outer group
            self.master.add_outer_handoff_tool(group.to_handoff_tool())
            # group handoff to sub group
            group.add_handoff_tool(self.to_handoff_tool())
